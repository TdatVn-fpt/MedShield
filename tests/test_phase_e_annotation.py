# tests/test_phase_e_annotation.py — Exercise blind packets for invented development notes.
import json
from pathlib import Path

import pytest

from ml.phase_e_annotation import choose_double_sample, finalize, prepare, read_source, reconcile
from ml.phase_e_intake import IntakeError


def _jsonl(rows: list[dict[str, object]]) -> bytes:
    """Serialize separate private records in the Phase E wire format."""
    return "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows).encode("utf-8")


def _source() -> bytes:
    """Make an illustrative source with CRLF, combining marks, and three declared strata."""
    return _jsonl(
        [
            {
                "note_id": f"dev-{i:02}",
                "text": f"🧪 ơ\u0301\r\nĐã ghi số 1234 trong mẫu {i}.",
                "family_id": "dev-family",
                "patient_group": f"dev-group-{i}",
                "source_group": "rare" if i == 9 else "ordinary",
                "slices": ["phone_outside_plan"] if i == 8 else [],
            }
            for i in range(10)
        ]
    )


def _receipt(ids: list[str], label: str | None = None) -> bytes:
    """Return a full receipt including entries with no annotated spans."""
    note = read_source(_source())["dev-08"].note
    start = note.text.index("1234")
    return _jsonl(
        [
            {
                "note_id": key,
                "entities": (
                    [{"start": start, "end": start + 4, "label": label}]
                    if label and key == note.note_id
                    else []
                ),
            }
            for key in ids
        ]
    )


def test_blind_packets_cover_rare_source_and_slice_without_labels(tmp_path: Path) -> None:
    """Verify repeatable stratum coverage and exact original text with no hint metadata."""
    notes = read_source(_source())
    sample = choose_double_sample(notes, 401)
    assert sample == choose_double_sample(dict(reversed(list(notes.items()))), 401)
    assert len(sample) >= 2 and {"dev-08", "dev-09"} <= set(sample)
    packet = tmp_path / "packets"
    assert prepare(_source(), packet, 401) == {"source_notes": 10, "double_notes": len(sample)}
    a = [json.loads(line) for line in (packet / "a-blind.jsonl").read_bytes().splitlines()]
    b = [json.loads(line) for line in (packet / "b-blind.jsonl").read_bytes().splitlines()]
    assert len(a) == 10 and [row["note_id"] for row in b] == sample
    assert all(set(item) == {"note_id", "text"} for item in a + b)
    assert all(item["text"] == notes[item["note_id"]].note.text for item in a + b)


def test_reconcile_and_finalize_require_real_decisions_for_exact_disputed_ids(
    tmp_path: Path,
) -> None:
    """Keep receipts distinct and require the adjudicator to resolve every disagreement."""
    source = _source()
    ids = sorted(read_source(source))
    packet, staging = tmp_path / "packets", tmp_path / "staging"
    prepare(source, packet, 401)
    manifest = (packet / "packet-manifest.json").read_bytes()
    sample = json.loads(manifest)["double_note_ids"]
    result = reconcile(source, manifest, _receipt(ids, "ID"), _receipt(sample, "PHONE"), staging)
    assert result["disputes"] == 1
    assert result["strict_iaa_micro"]["f1"] == 0 and not result["iaa_threshold_met"]
    output = tmp_path / "test.jsonl"
    with pytest.raises(IntakeError, match="Thiếu bản ghi"):
        finalize(staging, b"", output)
    assert not output.exists()
    assert finalize(staging, _receipt(["dev-08"], "PHONE"), output) == {
        key: result[key] for key in ("source_notes", "double_notes", "disputes")
    }
    gold = {row["note_id"]: row for row in map(json.loads, output.read_bytes().splitlines())}
    assert gold["dev-08"]["entities"][0]["label"] == "PHONE"
    assert "source_group" not in gold["dev-08"] and len(gold) == 10
    with pytest.raises(FileExistsError):
        finalize(staging, _receipt(["dev-08"], "PHONE"), output)


def test_reconcile_rejects_wrong_receipt_and_tampered_sampling_manifest(tmp_path: Path) -> None:
    """Reject omitted negative notes or altered sample selection before writing output."""
    source = _source()
    packet, staging = tmp_path / "packets", tmp_path / "staging"
    prepare(source, packet, 401)
    ids = sorted(read_source(source))
    manifest = json.loads((packet / "packet-manifest.json").read_bytes())
    sample = manifest["double_note_ids"]
    with pytest.raises(IntakeError, match="Thiếu bản ghi"):
        reconcile(
            source, json.dumps(manifest).encode(), _receipt(ids), _receipt(sample[1:]), staging
        )
    manifest["double_note_ids"] = ids
    with pytest.raises(IntakeError, match="Manifest"):
        reconcile(source, json.dumps(manifest).encode(), _receipt(ids), _receipt(ids), staging)
    assert not staging.exists()
