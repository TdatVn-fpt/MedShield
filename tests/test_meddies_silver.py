# tests/test_meddies_silver.py — Verify blind Unicode alignment and independent agreement.
import csv
import json
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock

import pytest

from ml.bio import GOLD_LABELS
from ml.meddies_annotator import (
    MODEL,
    PROMPT,
    REVISION,
    RUNTIME,
    _manifest,
    annotate,
    literal_spans,
    request_annotation,
)
from ml.meddies_lock import _check_split
from ml.meddies_recovery import RECOVERY_INSTRUCTION, digest, load_staged, stage
from ml.meddies_silver import (
    compare,
    llm_receipts,
    mapping_review,
    parse_returns,
    write_adjudication_packets,
)
from ml.meddies_split import _jsonl
from ml.phase_e_types import IntakeError


def test_llm_quotes_align_with_original_code_points() -> None:
    """Resolve repeated names and preserve emoji, CRLF and decomposed accents."""
    text = "🙂 Án\r\nÁn"
    mention = {"label": "NAME", "value": "Án", "occurrence": 2}
    assert literal_spans(text, {"entities": [mention]}) == [
        {"label": "NAME", "start": 7, "end": 10}
    ]
    with pytest.raises(IntakeError):
        literal_spans(text, {"entities": [dict(mention, value="Án")]})
    with pytest.raises(IntakeError):
        literal_spans(text, {"entities": [mention, mention]})


@pytest.mark.parametrize(
    ("reason", "diagnostic"),
    [("length", "bị cắt"), ("stop", "JSON không hợp lệ")],
)
def test_llm_failed_retries_report_a_safe_reason(
    monkeypatch: pytest.MonkeyPatch, reason: str, diagnostic: str
) -> None:
    """Keep actionable failure classifications without echoing private model content."""
    response = json.dumps(
        {
            "model": MODEL,
            "choices": [{"finish_reason": reason, "message": {"content": "PRIVATE-MARKER"}}],
        }
    ).encode()
    opener = Mock()
    opener.open.side_effect = [BytesIO(response) for _ in range(3)]
    monkeypatch.setattr("ml.meddies_annotator.build_opener", lambda *_: opener)
    with pytest.raises(IntakeError, match=diagnostic) as error:
        request_annotation("PRIVATE-NOTE", "guide", 18240)
    assert "PRIVATE" not in str(error.value)
    assert opener.open.call_count == 3


def test_llm_accepts_exactly_complete_json_at_token_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Recover a complete object emitted exactly at the token budget."""
    content = '{"entities":[{"label":"NAME","value":"Mai An","occurrence":1}]}'
    response = json.dumps(
        {"model": MODEL, "choices": [{"finish_reason": "length", "message": {"content": content}}]}
    ).encode()
    opener = Mock()
    opener.open.return_value = BytesIO(response)
    monkeypatch.setattr("ml.meddies_annotator.build_opener", lambda *_: opener)
    assert request_annotation("Mai An", "guide", 18240) == [
        {"start": 0, "end": 6, "label": "NAME"}
    ]
    assert opener.open.call_count == 1


def test_technical_retry_is_bound_to_the_exact_output_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stage a retry without replacing an existing checkpoint and verify the completed receipt."""
    packet = tmp_path / "packet.jsonl"
    packet.write_bytes(
        _jsonl([{"note_id": "one", "text": "Mai An"}, {"note_id": "two", "text": "Hẹn khám"}])
    )
    guide, destination, probe = (tmp_path / field for field in ("guide.txt", "out", "probe"))
    guide.write_bytes(b"guide")
    prompt = PROMPT + "guide"
    primary = _manifest(packet.read_bytes(), guide.read_bytes(), prompt)
    destination.mkdir()
    probe.mkdir()
    first = _jsonl([{"note_id": "one", "entities": [{"label": "NAME", "start": 0, "end": 6}]}])
    (probe / "candidate-b.jsonl").write_bytes(first)
    (probe / "receipt.json").write_text(
        json.dumps(
            {
                "kind": "blind_technical_recovery_probe",
                "position": 1,
                "model": MODEL,
                "revision": REVISION,
                "runtime": RUNTIME,
                "seed": primary["seed"],
                "max_tokens": 256,
                "source_sha256": primary["packet_sha256"],
                "guideline_sha256": primary["guideline_sha256"],
                "prompt_sha256": digest((prompt + RECOVERY_INSTRUCTION).encode()),
                "instruction": RECOVERY_INSTRUCTION,
            }
        ),
        encoding="utf-8",
    )
    (probe / "result.json").write_text(
        json.dumps({"finish_reason": "stop", "valid_spans": 1, "candidate_sha256": digest(first)}),
        encoding="utf-8",
    )
    assert stage(probe, destination, packet.read_bytes(), prompt, primary) == 1
    assert not (destination / "0001.json").exists()
    staged = destination / "recovery/0001.json"
    original = staged.read_bytes()
    changed = json.loads(original)
    changed["record"]["entities"][0]["unexpected"] = True
    changed["evidence"]["result"]["candidate_sha256"] = digest(_jsonl([changed["record"]]))
    staged.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(IntakeError, match="label, start và end"):
        load_staged(staged, primary, 1, "one", "Mai An", prompt)
    staged.write_bytes(original)
    send = Mock(return_value=[])
    monkeypatch.setattr("ml.meddies_annotator.request_annotation", send)
    annotate(packet, guide, destination, 18240)
    send.assert_called_once_with("Hẹn khám", prompt, 18240)
    output = (destination / "annotations-b.jsonl").read_bytes()
    sources = {"one": "Mai An", "two": "Hẹn khám"}
    _, receipt = llm_receipts(destination, output, 2, prompt, sources)
    final = json.loads(receipt)
    assert final["recoveries"][0]["result"]["candidate_sha256"] == digest(first)
    final["recoveries"][0]["request"]["prompt_sha256"] = None
    manifest = destination / "completion-manifest.json"
    manifest.write_text(json.dumps(final), encoding="utf-8")
    with pytest.raises(IntakeError, match="thử lại"):
        llm_receipts(destination, output, 2, prompt, sources)
    final = json.loads(receipt)
    reordered = b"".join(reversed(output.splitlines(keepends=True)))
    final["recoveries"][0]["request"]["position"] = 2
    final["annotations_sha256"] = digest(reordered)
    manifest.write_text(json.dumps(final), encoding="utf-8")
    with pytest.raises(IntakeError, match="thử lại"):
        llm_receipts(destination, reordered, 2, prompt, sources)


def test_iaa_is_strict_and_requires_complete_returns(tmp_path: Path) -> None:
    """A wrong boundary produces one FP, one FN and one dispute before adjudication."""
    texts = {"one": "Mai An", "two": "Bình"}
    first = b'{"note_id":"one","entities":[{"start":0,"end":6,"label":"NAME"}]}\n'
    second = b'{"note_id":"one","entities":[{"start":0,"end":3,"label":"NAME"}]}\n'
    unchanged = b'{"note_id":"two","entities":[{"start":0,"end":4,"label":"NAME"}]}\n'
    with pytest.raises(IntakeError):
        parse_returns(first, texts)
    differences, report = compare(
        parse_returns(first + unchanged, texts), parse_returns(second + unchanged, texts)
    )
    assert [row["note_id"] for row in differences] == ["one"]
    assert report["strict_micro"]["f1"] == 0.5
    assert report["disagreement_rate"] == 0.5
    assert report["confidence_interval_95"]["strict_f1"]["NAME"] == [0.0, 1.0]
    assert report["confidence_interval_95"]["disagreement_rate"] == [0.0, 1.0]
    assert not report["iaa_threshold_met"]
    write_adjudication_packets(tmp_path, "test", differences)
    packet = (tmp_path / "test-adjudication-packet.jsonl").read_bytes()
    assert packet == _jsonl([{"note_id": "one", "text": "Mai An"}])
    for annotator, end in (("a", 6), ("b", 3)):
        draft = json.loads((tmp_path / f"test-adjudication-draft-{annotator}.json").read_bytes())
        assert draft["packet_sha256"] == sha256(packet).hexdigest()
        assert draft["rows"] == [
            {
                "note_id": "one",
                "reviewed": False,
                "entities": [{"label": "NAME", "start": 0, "end": end}],
            }
        ]


def test_mapping_receipt_binds_every_sample(tmp_path: Path) -> None:
    """Accept 100 explicit decisions and reject a receipt from different sample bytes."""
    samples = json.dumps({label: [None] * 20 for label in sorted(GOLD_LABELS)}).encode()
    receipt = tmp_path / "receipt.csv"
    with receipt.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["sample_sha256", "label", "sample_index", "verdict", "reason"])
        for label in GOLD_LABELS:
            for i in range(1, 21):
                writer.writerow([sha256(samples).hexdigest(), label, i, "ok", ""])
    assert mapping_review(samples, receipt)["reviewed"] == 100
    with pytest.raises(IntakeError):
        mapping_review(samples + b" ", receipt)


def test_owner_csv_is_bound_to_the_original_note_id_and_value(tmp_path: Path) -> None:
    """Accept the approved CSV schema and reject altered values or absent correction reasons."""
    samples = {
        label: [{"note_id": f"{label}-{i}", "value": "Án, ví dụ"} for i in range(1, 21)]
        for label in GOLD_LABELS
    }
    encoded = json.dumps(samples).encode()
    receipt = tmp_path / "mapping-review.csv"
    with receipt.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["label", "sample_no", "note_id", "value", "verdict", "reason"])
        for label, group in samples.items():
            for index, sample in enumerate(group, 1):
                verdict = "needs_correction" if index == 1 else "ok"
                reason = "Sai biên" if index == 1 else ""
                writer.writerow(
                    [label, index, sample["note_id"], sample["value"], verdict, reason]
                )
    result = mapping_review(encoded, receipt)
    assert result["reviewed"] == 100
    assert result["corrections_by_label"] == dict.fromkeys(GOLD_LABELS, 1)
    original = receipt.read_text(encoding="utf-8-sig")
    for previous, replacement in (("Án, ví dụ", "Án, ví dụ"), ("Sai biên", "")):
        receipt.write_text(original.replace(previous, replacement, 1), encoding="utf-8-sig")
        with pytest.raises(IntakeError):
            mapping_review(encoded, receipt)


def test_lock_rechecks_iaa_support_and_adjudication(tmp_path: Path) -> None:
    """A mutated resolved annotation cannot pass the seal just because it meets support."""
    texts = [{"note_id": f"sample-{i}", "text": f"a b c d e f {i}"} for i in range(150)]
    entities = [
        {"start": 2 * i, "end": 2 * i + 1, "label": label}
        for i, label in enumerate([*GOLD_LABELS, "NAME"])
    ]
    returns = _jsonl([{"note_id": row["note_id"], "entities": entities} for row in texts])
    packet_sha = sha256(_jsonl(texts)).hexdigest()
    manifest = {"packet_sha256": {"test-blind.jsonl": packet_sha}, "split_counts": {"test": 150}}
    (tmp_path / "test-blind.jsonl").write_bytes(_jsonl(texts))
    (tmp_path / "test-a.jsonl").write_bytes(returns)
    qwen = tmp_path / "test-qwen"
    qwen.mkdir()
    (qwen / "annotations-b.jsonl").write_bytes(returns)
    request = qwen / "request-manifest.json"
    request.write_text(
        json.dumps(
            {
                "model": MODEL,
                "model_revision": REVISION,
                "runtime": RUNTIME,
                "packet_sha256": packet_sha,
                "guideline_sha256": "test-guideline",
                "prompt_sha256": "test-prompt",
            }
        ),
        encoding="utf-8",
    )
    (qwen / "completion-manifest.json").write_text(
        json.dumps(
            {
                "status": "complete",
                "notes": 150,
                "request_sha256": sha256(request.read_bytes()).hexdigest(),
                "annotations_sha256": sha256(returns).hexdigest(),
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "test-adjudication.jsonl").touch()
    locked = tmp_path / "test-resolved.jsonl"
    resolved = [dict(row, entities=entities) for row in texts]
    locked.write_bytes(_jsonl(resolved))
    result = _check_split("test", tmp_path, tmp_path, manifest, "test-guideline", "test-prompt")
    assert result["strict_micro"]["f1"] == 1.0
    assert result["participant_reviewed_count"] == 150
    resolved[0]["entities"] = entities[1:]
    locked.write_bytes(_jsonl(resolved))
    with pytest.raises(IntakeError):
        _check_split("test", tmp_path, tmp_path, manifest, "test-guideline", "test-prompt")
    locked.write_bytes(_jsonl([dict(row, entities=entities) for row in texts]))
    (qwen / "annotations-b.jsonl").write_bytes(returns + b"\n")
    with pytest.raises(IntakeError, match="Biên nhận"):
        _check_split("test", tmp_path, tmp_path, manifest, "test-guideline", "test-prompt")
