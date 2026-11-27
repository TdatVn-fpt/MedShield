# tests/test_meddies_probe.py — Verify technical retries require a logged failure and valid output.
import json
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock

import pytest

from ml.meddies_annotator import MODEL, PROMPT, REVISION, RUNTIME, _manifest
from ml.meddies_offset_grammar import OFFSET_INSTRUCTION, render_qwen_chat, source_offset_grammar
from ml.meddies_probe import _infer, _infer_offset, probe
from ml.meddies_recovery import RECOVERY_INSTRUCTION, digest, load_staged, stage
from ml.phase_e_types import IntakeError


def test_probe_generates_only_for_logged_failure_and_stages_full_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify an expanded token retry uses the frozen packet and records its own limit."""
    packet_dir = tmp_path / "step3-source-isolated"
    packet_dir.mkdir()
    packet = b'{"note_id":"one","text":"Mai An"}\n'
    (packet_dir / "validation-blind.jsonl").write_bytes(packet)
    guide = tmp_path / "guide.txt"
    guide.write_bytes(b"guide")
    dest = tmp_path / "step4" / "validation-qwen"
    dest.mkdir(parents=True)
    (dest / "request-manifest.json").write_text(
        json.dumps(_manifest(packet, b"guide", PROMPT + "guide")), encoding="utf-8"
    )
    log = tmp_path / "step4" / "main.log"
    log.write_text("1/1 complete\n", encoding="utf-8")
    detect = Mock(
        return_value=(
            {"finish_reason": "stop", "valid_spans": 1},
            [{"label": "NAME", "start": 0, "end": 6}],
        )
    )
    monkeypatch.setattr("ml.meddies_probe._infer", detect)
    with pytest.raises(IntakeError, match="nhật ký"):
        probe(tmp_path, "validation", 1, guide, 512, log)
    detect.assert_not_called()
    log.write_text("1/1 needs retry: invalid JSON\n", encoding="utf-8")
    assert probe(tmp_path, "validation", 1, guide, 512, log)
    assert detect.call_args.args[2] == 512
    staged = json.loads((dest / "recovery/0001.json").read_bytes())
    assert staged["evidence"]["request"]["max_tokens"] == 512
    assert not (dest / "0001.json").exists()


def test_probe_reports_literal_failure_without_echoing_the_notes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Identify a fabricated quotation while withholding both private strings."""
    content = '{"entities":[{"label":"NAME","value":"PRIVATE-QUOTE","occurrence":1}]}'
    response = {
        "model": MODEL,
        "choices": [{"finish_reason": "stop", "message": {"content": content}}],
    }
    opener = Mock()
    opener.open.return_value = BytesIO(json.dumps(response).encode())
    monkeypatch.setattr("ml.meddies_probe.build_opener", lambda *_: opener)
    status, spans = _infer("PRIVATE-NOTE", "guide", 512)
    assert spans is None and status["error"] == "invalid_literal_spans"
    assert "không khớp" in status["validation_error"]
    assert "PRIVATE" not in json.dumps(status)


def test_stage_native_offset_recovery_binds_grammar_to_original_note(tmp_path: Path) -> None:
    """Accept an exact source-coupled grammar and reject changed grammar evidence."""
    note = '🙂\r\nMai "An"'
    packet = (json.dumps({"note_id": "one", "text": note}, ensure_ascii=False) + "\n").encode()
    out, destination = tmp_path / "probe", tmp_path / "out"
    out.mkdir()
    destination.mkdir()
    prompt = PROMPT + "guide"
    primary = _manifest(packet, b"guide", prompt)
    grammar = source_offset_grammar(note)
    assert "position ::= p0 | p3" in grammar
    assert 'q1 ::= "\\\\r" q2' in grammar
    assert 'q2 ::= "\\\\n" q3' in grammar
    assert "p3 ::= " in grammar
    instruction = RECOVERY_INSTRUCTION + OFFSET_INSTRUCTION
    metadata = {
        "kind": "blind_native_source_offset_probe",
        "position": 1,
        "model": MODEL,
        "revision": REVISION,
        "runtime": RUNTIME,
        "seed": primary["seed"],
        "max_tokens": 512,
        "source_sha256": digest(packet),
        "guideline_sha256": digest(b"guide"),
        "prompt_sha256": digest((prompt + instruction).encode()),
        "rendered_prompt_sha256": digest(render_qwen_chat(prompt + instruction, note).encode()),
        "grammar_sha256": digest(grammar.encode()),
        "instruction": instruction,
    }
    text = b'{"note_id": "one", "entities": [{"label": "NAME", "start": 3, "end": 11}]}\n'
    (out / "receipt.json").write_text(json.dumps(metadata), encoding="utf-8")
    (out / "candidate-b.jsonl").write_bytes(text)
    (out / "result.json").write_text(
        json.dumps(
            {
                "candidate_sha256": digest(text),
                "valid_spans": 1,
                "parsed_spans": 1,
                "stop_type": "eos",
                "grammar_reported": True,
                "grammar_matches": True,
            }
        ),
        encoding="utf-8",
    )
    assert stage(out, destination, packet, prompt, primary) == 1
    path = destination / "recovery/0001.json"
    original = path.read_bytes()
    for field in ("grammar_sha256", "rendered_prompt_sha256"):
        saved = json.loads(original)
        saved["evidence"]["request"][field] = "a" * 64
        path.write_text(json.dumps(saved), encoding="utf-8")
        with pytest.raises(IntakeError, match="Biên nhận"):
            load_staged(path, primary, 1, "one", note, prompt)


def test_native_request_requires_matching_template_and_echoed_grammar(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercise the native transport and validate original code-point spans."""
    note, prompt = "🙂 Mai An", "guide"
    grammar = source_offset_grammar(note)
    completed = {
        "model": MODEL,
        "stop_type": "eos",
        "generation_settings": {"grammar": grammar},
        "content": '{"entities":[{"label":"NAME","start":2,"value":"Mai An"}]}',
    }
    post = Mock(side_effect=[{"prompt": render_qwen_chat(prompt, note)}, completed])
    monkeypatch.setattr("ml.meddies_probe._post", post)
    status, spans = _infer_offset(note, prompt, grammar)
    assert status["grammar_matches"] is True
    assert spans == [{"label": "NAME", "start": 2, "end": 8}]
    assert post.call_args.args[1]["grammar"] == grammar
    partial = {**completed, "stop_type": "limit", "content": '{"entities":['}
    post.side_effect = [{"prompt": render_qwen_chat(prompt, note)}, partial]
    assert _infer_offset(note, prompt, grammar) == (
        {"stop_type": "limit", "error": "incomplete_or_invalid_json"},
        None,
    )
    completed["generation_settings"] = {"grammar": ""}
    post.side_effect = [{"prompt": render_qwen_chat(prompt, note)}, completed]
    assert _infer_offset(note, prompt, grammar) == ({"error": "runtime_grammar_mismatch"}, None)
    post.side_effect = [{"prompt": "unexpected"}]
    assert _infer_offset(note, prompt, grammar) == ({"error": "runtime_template_mismatch"}, None)
