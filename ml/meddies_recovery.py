# ml/meddies_recovery.py — Bind separately retried blind Qwen annotations to their source.
import json
from hashlib import sha256
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from ml.dataset import parse_note
from ml.meddies_offset_grammar import OFFSET_INSTRUCTION, render_qwen_chat, source_offset_grammar
from ml.phase_e_intake import _rows
from ml.phase_e_types import IntakeError

RECOVERY_INSTRUCTION = (
    "\nOutput compact JSON. List each actual identifying span once, in source order. "
    "Never copy a full line of context. A value is only the identifying substring. "
    "Finish the object immediately after the last span. Follow the same five-label guideline.\n"
)
RECOVERY_TOKEN_LIMITS = (256, 512)


def digest(data: bytes) -> str:
    """Return SHA-256 for exact packet and receipt bytes."""
    return sha256(data).hexdigest()


def prompt_digest(primary_prompt: str) -> str:
    """Hash the exact primary prompt plus the fixed blind recovery instruction."""
    return digest((primary_prompt + RECOVERY_INSTRUCTION).encode())


def _verify(
    evidence: dict[str, Any],
    primary: dict[str, Any],
    position: int,
    line: bytes,
    prompt: str,
    text: str,
) -> None:
    """Match recovery provenance against the recorded model, source and exact output row."""
    if set(evidence) != {"request", "result", "primary_prompt_sha256"}:
        raise IntakeError("Biên nhận thử lại có trường không hợp lệ.")
    request, result = evidence["request"], evidence["result"]
    if not isinstance(request, dict) or not isinstance(result, dict):
        raise IntakeError("Biên nhận thử lại sai cấu trúc.")
    limit = request.get("max_tokens")
    if type(limit) is not int or limit not in RECOVERY_TOKEN_LIMITS:
        raise IntakeError("Giới hạn token của lượt thử lại chưa được đăng ký.")
    kind = request.get("kind")
    expected = {
        "kind": kind,
        "model": primary["model"],
        "revision": primary["model_revision"],
        "runtime": primary["runtime"],
        "seed": primary["seed"],
        "source_sha256": primary["packet_sha256"],
        "guideline_sha256": primary["guideline_sha256"],
        "position": position,
        "max_tokens": limit,
    }
    row = json.loads(line)
    regions = len(row["entities"])
    completed = {"candidate_sha256": digest(line), "valid_spans": regions}
    if kind == "blind_native_source_offset_probe":
        if limit != 512:
            raise IntakeError("Giới hạn token của lượt ngữ pháp không khớp bản chốt.")
        instruction = RECOVERY_INSTRUCTION + OFFSET_INSTRUCTION
        native_prompt = prompt + instruction
        expected.update(
            instruction=instruction,
            prompt_sha256=digest(native_prompt.encode()),
            grammar_sha256=digest(source_offset_grammar(text).encode()),
            rendered_prompt_sha256=digest(render_qwen_chat(native_prompt, text).encode()),
        )
        stop = result.get("stop_type")
        if stop not in {"eos", "word", "limit"}:
            raise IntakeError("Lượt ngữ pháp chưa kết thúc hợp lệ.")
        if result.get("grammar_reported") is not True or result.get("grammar_matches") is not True:
            raise IntakeError("Runtime chưa xác nhận đúng ngữ pháp thử lại.")
        completed.update(
            stop_type=stop, grammar_reported=True, grammar_matches=True, parsed_spans=regions
        )
    elif kind == "blind_technical_recovery_probe":
        expected.update(instruction=RECOVERY_INSTRUCTION, prompt_sha256=prompt_digest(prompt))
        finish = result.get("finish_reason")
        if finish not in {"stop", "length"}:
            raise IntakeError("Lượt thử lại chưa kết thúc hợp lệ.")
        completed["finish_reason"] = finish
    else:
        raise IntakeError("Kiểu biên nhận thử lại chưa được hỗ trợ.")
    if (
        request != expected
        or evidence["primary_prompt_sha256"] != primary["prompt_sha256"]
        or digest(prompt.encode()) != primary["prompt_sha256"]
        or result != completed
    ):
        raise IntakeError("Biên nhận thử lại không khớp gói, mô hình hoặc dòng nhãn.")


def _validate_record(record: dict[str, Any], key: str, text: str) -> None:
    """Validate exact return fields and non-overlapping code-point offsets."""
    if set(record) != {"note_id", "entities"} or record["note_id"] != key:
        raise IntakeError("Nhãn thử lại sai cấu trúc hoặc mã ghi chú.")
    if not isinstance(record["entities"], list) or any(
        not isinstance(span, dict) or set(span) != {"label", "start", "end"}
        for span in record["entities"]
    ):
        raise IntakeError("Vùng thử lại chỉ được có label, start và end.")
    try:
        parse_note(dict(record, family_id="unverified", text=text))
    except (TypeError, ValueError):
        raise IntakeError("Vị trí vùng thử lại không hợp lệ.") from None


def stage(
    probe: Path, destination: Path, packet: bytes, prompt: str, primary: dict[str, Any]
) -> int:
    """Stage a verified blind result separately from any existing primary checkpoint."""
    request = json.loads((probe / "receipt.json").read_bytes())
    result = json.loads((probe / "result.json").read_bytes())
    position = request["position"]
    notes = _rows(packet, "gói gán mù để thử lại")
    if type(position) is not int or not 1 <= position <= len(notes):
        raise IntakeError("Số thứ tự thử lại ngoài gói.")
    line = (probe / "candidate-b.jsonl").read_bytes()
    evidence = {
        "request": request,
        "result": result,
        "primary_prompt_sha256": digest(prompt.encode()),
    }
    if primary["packet_sha256"] != digest(packet):
        raise IntakeError("Gói thử lại không khớp bản chốt.")
    source = notes[position - 1]
    _verify(evidence, primary, position, line, prompt, source["text"])
    records = _rows(line, "nhãn thử lại")
    if len(records) != 1:
        raise IntakeError("Nhãn thử lại phải chứa đúng một dòng chuẩn.")
    record = records[0]
    _validate_record(record, source["note_id"], source["text"])
    if line != (json.dumps(record, ensure_ascii=False) + "\n").encode():
        raise IntakeError("Dòng thử lại không ở dạng tuần tự hóa chuẩn.")
    if (destination / f"{position:04}.json").exists():
        raise IntakeError("Ghi chú đã có checkpoint của lượt chính.")
    staged = destination / "recovery"
    staged.mkdir(exist_ok=True)
    payload = (
        json.dumps({"record": record, "evidence": evidence}, ensure_ascii=False) + "\n"
    ).encode()
    with NamedTemporaryFile(mode="wb", dir=staged, delete=False) as stream:
        temporary = Path(stream.name)
    try:
        temporary.write_bytes(payload)
        (staged / f"{position:04}.json").hardlink_to(temporary)
    finally:
        temporary.unlink(missing_ok=True)
    return position


def load_staged(
    path: Path, primary: dict[str, Any], position: int, key: str, text: str, prompt: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Read a staged record and verify its provenance without touching a primary checkpoint."""
    payload = json.loads(path.read_bytes())
    record, evidence = payload["record"], payload["evidence"]
    _validate_record(record, key, text)
    line = (json.dumps(record, ensure_ascii=False) + "\n").encode()
    _verify(evidence, primary, position, line, prompt, text)
    return record, evidence


def verify_completion(
    receipts: list[dict[str, Any]],
    primary: dict[str, Any],
    outputs: bytes,
    prompt: str,
    sources: dict[str, str],
) -> None:
    """Reject duplicated or detached recovery evidence in the final output manifest."""
    if not isinstance(receipts, list) or not receipts:
        raise IntakeError("Danh sách thử lại trong manifest không hợp lệ.")
    rows = outputs.splitlines(keepends=True)
    source_order = tuple(sources)
    if len(rows) != len(source_order):
        raise IntakeError("Số dòng nhãn thử lại không khớp gói mù.")
    seen = set()
    for evidence in receipts:
        position = evidence["request"]["position"]
        if type(position) is not int or not 1 <= position <= len(rows) or position in seen:
            raise IntakeError("Số thứ tự thử lại trùng hoặc ngoài bộ nhãn.")
        line = rows[position - 1]
        if json.loads(line)["note_id"] != source_order[position - 1]:
            raise IntakeError("Vị trí thử lại không khớp thứ tự mã trong gói mù.")
        _verify(evidence, primary, position, line, prompt, sources[source_order[position - 1]])
        seen.add(position)


def llm_receipts(
    directory: Path,
    outputs: bytes,
    count: int,
    primary_prompt: str | None = None,
    sources: dict[str, str] | None = None,
) -> tuple[bytes, bytes]:
    """Bind the completed blind returns to the exact request and completion evidence."""
    request = (directory / "request-manifest.json").read_bytes()
    completion = (directory / "completion-manifest.json").read_bytes()
    metadata = json.loads(completion)
    if not isinstance(metadata, dict):
        raise IntakeError("Biên nhận hoàn thành LLM sai cấu trúc.")
    if "recoveries" in metadata:
        if primary_prompt is None or sources is None:
            raise IntakeError("Thiếu prompt hoặc văn bản nguồn để đối chiếu thử lại.")
        verify_completion(
            metadata.pop("recoveries"),
            json.loads(request),
            outputs,
            primary_prompt,
            sources,
        )
    if metadata != {
        "status": "complete",
        "notes": count,
        "request_sha256": digest(request),
        "annotations_sha256": digest(outputs),
    }:
        raise IntakeError("Biên nhận hoàn thành LLM khác tệp nhãn hoặc manifest yêu cầu.")
    return request, completion
