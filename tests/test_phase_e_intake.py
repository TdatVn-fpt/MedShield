# tests/test_phase_e_intake.py — Verify private bundle structure, adjudication and immutable bytes.
import json
import subprocess
import sys
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from ml.bio import GOLD_LABELS
from ml.phase_e_annotation import prepare
from ml.phase_e_intake import MANIFEST_NAME, SLICES, IntakeError, inspect_intake


def _write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write synthetic test-only records as UTF-8 LF JSONL."""
    path.write_bytes("".join(json.dumps(row) + "\n" for row in rows).encode())


def _note(split: str, number: int) -> dict[str, Any]:
    """Create a fixture record with grouped families and simple code point intervals."""
    return {
        "note_id": f"{split}-{number}",
        "patient_group": f"{split}-patient-{number}",
        "family_id": f"{split}-family-{number % 3}",
        "text": f"ơ a b c d e 🧭{split}-{number}",
        "entities": [
            {"start": 2 * i, "end": 2 * i + 1, "label": label}
            for i, label in enumerate((*GOLD_LABELS, "NAME"))
        ],
        "slices": list(SLICES),
    }


def _sample(path: Path, test: list[dict[str, Any]]) -> tuple[bytes, set[str]]:
    """Preregister a fixture sample before assigning any of the synthetic label receipts."""
    source = path / "source.jsonl"
    _write_rows(
        source,
        [
            {**{k: v for k, v in row.items() if k != "entities"}, "source_group": "fixture"}
            for row in test
        ],
    )
    prepare(source.read_bytes(), path / "packets", 17)
    packet = (path / "packets/packet-manifest.json").read_bytes()
    (path / "packet-manifest.json").write_bytes(packet)
    return packet, set(json.loads(packet)["double_note_ids"])


@pytest.fixture
def bundle(tmp_path: Path) -> Path:
    """Build a synthetic schema fixture; its role aliases and digests are test placeholders."""
    metadata = {
        "schema_version": 1,
        "source_type": "independent_generator",
        "source_evidence_sha256": "a" * 64,
        "owner_approval_sha256": "b" * 64,
        "independent_of_detection": True,
        "human_blind_double_annotation": True,
        "annotator_a": "fixture-a",
        "annotator_b": "fixture-b",
        "adjudicator": "fixture-arbitrator",
        "participant_reviewed_count": 0,
    }
    _write_rows(
        tmp_path / "train-groups.jsonl", [{"patient_group": "train-1", "family_id": "train-f1"}]
    )
    _write_rows(tmp_path / "validation.jsonl", [_note("val", i) for i in range(100)])
    test = [_note("test", i) for i in range(150)]
    packet, sample = _sample(tmp_path, test)
    metadata["packet_manifest_sha256"] = sha256(packet).hexdigest()
    (tmp_path / "provenance.json").write_text(json.dumps(metadata), encoding="utf-8")
    _write_rows(tmp_path / "test.jsonl", test)
    a = [
        {"note_id": note["note_id"], "entities": note["entities"]}
        for note in test
        if note["note_id"] in sample
    ]
    b = [dict(note) for note in a]
    b[0]["entities"] = b[0]["entities"][1:]
    _write_rows(tmp_path / "annotations-a.jsonl", a)
    _write_rows(tmp_path / "annotations-b.jsonl", b)
    _write_rows(tmp_path / "adjudication.jsonl", a[:1])
    return tmp_path


def _run(mode: str, bundle: Path) -> subprocess.CompletedProcess[bytes]:
    """Invoke the real intake CLI and capture its status and private-output boundary."""
    return subprocess.run(
        [sys.executable, "-X", "utf8", "-m", "ml.phase_e_intake", mode, str(bundle)],
        check=False,
        capture_output=True,
    )


def test_seal_verify_and_detect_byte_change(bundle: Path) -> None:
    """Check score arithmetic and detect a byte change even when parsed inputs stay the same."""
    sealed = _run("seal", bundle)
    assert sealed.returncode == 0, sealed.stderr
    manifest_path = bundle / MANIFEST_NAME
    manifest = json.loads(manifest_path.read_bytes())
    assert manifest["counts"]["test_notes"] == 150
    assert manifest["agreement"]["strict_iaa"]["f1"] == pytest.approx(358 / 359)
    assert manifest["agreement"]["adjudicated_notes"] == 1
    assert b"test-patient-0" not in sealed.stdout
    assert _run("verify", bundle).returncode == 0
    assert _run("seal", bundle).returncode != 0
    metadata = bundle / "provenance.json"
    metadata.write_bytes(metadata.read_bytes() + b"\n")
    assert _run("verify", bundle).returncode != 0


def test_reject_patient_or_family_overlap(bundle: Path) -> None:
    """Refuse a training inventory with a locked test group even if other IDs differ."""
    _write_rows(
        bundle / "train-groups.jsonl",
        [{"patient_group": "train-1", "family_id": "test-family-0"}],
    )
    with pytest.raises(IntakeError, match="trùng giữa"):
        inspect_intake(bundle)


def test_reject_wrong_adjudication_and_low_iaa(bundle: Path) -> None:
    """Require an adjudication for every disagreement and refuse a low agreement bundle."""
    _write_rows(bundle / "adjudication.jsonl", [])
    with pytest.raises(IntakeError, match="Thiếu hoặc thừa"):
        inspect_intake(bundle)
    notes = [
        json.loads(line) for line in (bundle / "annotations-a.jsonl").read_bytes().splitlines()
    ]
    _write_rows(
        bundle / "annotations-b.jsonl",
        [{"note_id": note["note_id"], "entities": []} for note in notes],
    )
    _write_rows(
        bundle / "adjudication.jsonl",
        [{"note_id": note["note_id"], "entities": note["entities"]} for note in notes],
    )
    with pytest.raises(IntakeError, match="IAA strict entity-F1 dưới 0,85"):
        inspect_intake(bundle)


def test_reject_replacement_of_preregistered_agreement_sample(bundle: Path) -> None:
    """Reject perfectly agreeing annotators who returned a different 20% of the corpus."""
    packet = json.loads((bundle / "packet-manifest.json").read_bytes())
    sample = set(packet["double_note_ids"])
    alternate = [row for i in range(150) if (row := _note("test", i))["note_id"] not in sample][
        :30
    ]
    received = [{"note_id": row["note_id"], "entities": row["entities"]} for row in alternate]
    for name in ("annotations-a.jsonl", "annotations-b.jsonl"):
        _write_rows(bundle / name, received)
    _write_rows(bundle / "adjudication.jsonl", [])
    with pytest.raises(IntakeError, match="đúng mẫu"):
        inspect_intake(bundle)


def test_reject_edited_source_and_packet_bytes(bundle: Path) -> None:
    """Reject text edits and packet bytes that differ from the preregistered originals."""
    test = bundle / "test.jsonl"
    before = test.read_bytes()
    rows = [json.loads(line) for line in before.splitlines()]
    rows[-1]["text"] += " altered"
    _write_rows(test, rows)
    with pytest.raises(IntakeError, match="khác nguồn lấy mẫu"):
        inspect_intake(bundle)
    test.write_bytes(before)
    packet = bundle / "packet-manifest.json"
    packet.write_bytes(packet.read_bytes() + b"\n")
    with pytest.raises(IntakeError, match="SHA-256 manifest mẫu"):
        inspect_intake(bundle)
    rejected = _run("check", bundle)
    assert rejected.returncode == 1 and rejected.stderr.startswith(b"Phase E: SHA-256")
    assert b"Traceback" not in rejected.stderr
