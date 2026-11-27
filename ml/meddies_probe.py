# ml/meddies_probe.py — Retry a documented blind Qwen output failure locally.
import json
from argparse import ArgumentParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

from ml.meddies_annotator import MODEL, PROMPT, REVISION, RUNTIME, SCHEMA, _manifest, literal_spans
from ml.meddies_offset_grammar import (
    OFFSET_INSTRUCTION,
    render_qwen_chat,
    source_offset_grammar,
    source_offset_spans,
)
from ml.meddies_recovery import (
    RECOVERY_INSTRUCTION,
    RECOVERY_TOKEN_LIMITS,
    digest,
    prompt_digest,
    stage,
)
from ml.meddies_silver import packet_rows
from ml.phase_e_types import IntakeError


def _record_failure(log: Path, position: int, count: int) -> None:
    """Require an observed failed note before sending any blind recovery request."""
    prefix = f"{position}/{count} needs retry"
    lines = log.read_text(encoding="utf-8-sig").splitlines()
    if not any(line == prefix or line.startswith(prefix + ":") for line in lines):
        raise IntakeError("Chưa có lỗi đầu ra cho vị trí này trong nhật ký lượt chính.")


def _post(route: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Send a request to the fixed loopback runtime without logging prompt text."""
    request = Request(
        f"http://127.0.0.1:18240/{route}",
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json"},
    )
    with build_opener(ProxyHandler({})).open(request, timeout=285) as response:
        result = json.load(response)
    if not isinstance(result, dict):
        raise ValueError("Invalid native response envelope")
    return result


def _infer(
    note: str, prompt: str, limit: int
) -> tuple[dict[str, Any], list[dict[str, Any]] | None]:
    """Request one compact JSON completion and report only its outcome and validated regions."""
    payload = {
        "model": MODEL,
        "temperature": 0,
        "seed": 20261126,
        "max_tokens": limit,
        "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": note}],
        "response_format": {"type": "json_schema", "json_schema": {"schema": SCHEMA}},
    }
    try:
        result = _post("v1/chat/completions", payload)
        if result.get("model") != MODEL:
            return {"error": "model_mismatch"}, None
        choice = result["choices"][0]
        finish = choice["finish_reason"]
        if finish not in {"stop", "length"}:
            return {"error": "unsupported_finish_reason"}, None
    except (OSError, ValueError, KeyError, TypeError, IndexError):
        return {"error": "runtime_or_envelope"}, None
    try:
        spans = literal_spans(note, json.loads(choice["message"]["content"]))
    except IntakeError as exc:
        return {
            "finish_reason": finish,
            "error": "invalid_literal_spans",
            "validation_error": str(exc),
        }, None
    except (ValueError, KeyError, TypeError):
        return {"finish_reason": finish, "error": "incomplete_or_invalid_json"}, None
    return {"finish_reason": finish, "valid_spans": len(spans)}, spans


def _infer_offset(
    note: str, prompt: str, grammar: str
) -> tuple[dict[str, Any], list[dict[str, Any]] | None]:
    """Use the native endpoint and verify its template, grammar and source spans."""
    rendered = render_qwen_chat(prompt, note)
    try:
        template = _post(
            "apply-template",
            {
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": note},
                ]
            },
        )
        if template.get("prompt") != rendered:
            return {"error": "runtime_template_mismatch"}, None
        result = _post(
            "completion",
            {
                "prompt": rendered,
                "temperature": 0,
                "seed": 20261126,
                "n_predict": 512,
                "grammar": grammar,
            },
        )
        stop = result.get("stop_type")
        if result.get("model") != MODEL or stop not in {"eos", "word", "limit"}:
            return {"error": "runtime_or_envelope"}, None
        if result.get("generation_settings", {}).get("grammar") != grammar:
            return {"error": "runtime_grammar_mismatch"}, None
    except HTTPError as exc:
        return {"error": "runtime_http_error", "http_status": exc.code}, None
    except TimeoutError:
        return {"error": "runtime_timeout"}, None
    except (OSError, TypeError, ValueError, KeyError, AttributeError):
        return {"error": "runtime_or_envelope"}, None
    try:
        spans = source_offset_spans(note, json.loads(result["content"]))
    except IntakeError as exc:
        return {"stop_type": stop, "error": "invalid_offsets", "validation_error": str(exc)}, None
    except (ValueError, KeyError, TypeError):
        return {"stop_type": stop, "error": "incomplete_or_invalid_json"}, None
    return {
        "stop_type": stop,
        "grammar_reported": True,
        "grammar_matches": True,
        "parsed_spans": len(spans),
        "valid_spans": len(spans),
    }, spans


def probe(
    root: Path,
    split: str,
    position: int,
    guideline: Path,
    limit: int,
    log: Path,
    *,
    source_offset: bool = False,
) -> bool:
    """Bind one failed note to exact prompt and packet bytes, then stage valid output only."""
    if limit not in RECOVERY_TOKEN_LIMITS:
        raise IntakeError("Giới hạn token thử lại chưa được đăng ký.")
    if source_offset and limit != 512:
        raise IntakeError("Lượt ngữ pháp cần giới hạn 512 token.")
    packet = (root / "step3-source-isolated" / f"{split}-blind.jsonl").read_bytes()
    notes = list(packet_rows(packet).items())
    if not 1 <= position <= len(notes):
        raise IntakeError("Số thứ tự thử lại ngoài gói.")
    _record_failure(log, position, len(notes))
    key, note = notes[position - 1]
    guide = guideline.read_bytes()
    base = PROMPT + guide.decode("utf-8")
    destination = root / "step4" / f"{split}-qwen"
    for path in (
        destination / f"{position:04}.json",
        destination / "recovery" / f"{position:04}.json",
    ):
        if path.exists():
            raise IntakeError("Ghi chú đã có kết quả, không cần thử lại.")
    primary = _manifest(packet, guide, base)
    if json.loads((destination / "request-manifest.json").read_bytes()) != primary:
        raise IntakeError("Biên nhận lượt chính không khớp gói và guideline thử lại.")
    tag = f"source-offset-{position:04d}" if source_offset else f"probe-{position:04d}-{limit}"
    work = root / "step4" / f"{split}-qwen-recovery-{tag}"
    work.mkdir()
    receipt = {
        "kind": "blind_technical_recovery_probe",
        "position": position,
        "model": MODEL,
        "revision": REVISION,
        "runtime": RUNTIME,
        "seed": primary["seed"],
        "max_tokens": limit,
        "source_sha256": digest(packet),
        "prompt_sha256": prompt_digest(base),
        "guideline_sha256": digest(guide),
        "instruction": RECOVERY_INSTRUCTION,
    }
    if source_offset:
        instruction = RECOVERY_INSTRUCTION + OFFSET_INSTRUCTION
        native_prompt = base + instruction
        grammar = source_offset_grammar(note)
        receipt.update(
            kind="blind_native_source_offset_probe",
            instruction=instruction,
            prompt_sha256=digest(native_prompt.encode()),
            rendered_prompt_sha256=digest(render_qwen_chat(native_prompt, note).encode()),
            grammar_sha256=digest(grammar.encode()),
        )
    (work / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    if source_offset:
        status, spans = _infer_offset(note, native_prompt, grammar)
    else:
        status, spans = _infer(note, base + RECOVERY_INSTRUCTION, limit)
    if spans is not None:
        line = (
            json.dumps({"note_id": key, "entities": spans}, ensure_ascii=False) + "\n"
        ).encode()
        (work / "candidate-b.jsonl").write_bytes(line)
        status["candidate_sha256"] = digest(line)
    (work / "result.json").write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    if spans is not None:
        stage(work, destination, packet, base, primary)
    print(json.dumps(status), flush=True)
    return spans is not None


def main() -> None:
    """Retry one previously logged failure in the local workspace without logging text."""
    parser = ArgumentParser(description="Thử lại một lỗi đầu ra của lượt Qwen mù.")
    parser.add_argument("split", choices=("validation", "test"))
    parser.add_argument("position", type=int)
    parser.add_argument("log", type=Path)
    parser.add_argument("--max-tokens", type=int, choices=RECOVERY_TOKEN_LIMITS)
    parser.add_argument("--source-offset", action="store_true")
    repo = Path(__file__).resolve().parents[1]
    parser.add_argument("--guideline", type=Path, default=repo / "docs/annotation-guide.md")
    args = parser.parse_args()
    local = (repo / "artifacts/local/meddies").resolve()
    if not args.log.resolve().is_relative_to(local / "step4"):
        parser.error("Nhật ký lượt chính phải nằm trong thư mục cục bộ Bước 4.")
    try:
        limit = args.max_tokens or (512 if args.source_offset else 256)
        complete = probe(
            local,
            args.split,
            args.position,
            args.guideline,
            limit,
            args.log,
            source_offset=args.source_offset,
        )
    except IntakeError as exc:
        parser.exit(1, f"Meddies: {exc}\n")
    except (OSError, ValueError, KeyError, TypeError):
        parser.exit(1, "Meddies: Không đọc được nguồn hoặc biên nhận thử lại.\n")
    if not complete:
        parser.exit(2, "Meddies: Thử lại chưa tạo được nhãn hợp lệ.\n")


if __name__ == "__main__":
    main()
