# tests/test_phase_e_evaluate.py — Verify Phase E scoring on synthetic protocol fixtures.
import json
import subprocess
import sys
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from ml.bio import GOLD_LABELS, Span
from ml.dataset import Note
from ml.evaluation_metrics import MIN_DRAWS
from ml.phase_e_evaluate import evaluate, gate_gaps, parse_predictions
from ml.phase_e_intake import MANIFEST_NAME, SLICES, IntakeError, Record


def _envelope() -> dict[str, Any]:
    """Describe an observed run using opaque fixture hashes and no annotation text."""
    return {
        "schema_version": 1,
        "test_sha256": "a" * 64,
        "manifest_sha256": "b" * 64,
        "selection_validation_sha256": "c" * 64,
        "selected_before_test": True,
        "observed_inference": True,
        "method": "hybrid",
        "mode": "hybrid",
        "model_checkpoint_sha256": "d" * 64,
        "candidate_revision_sha256": "e" * 64,
        "selection_evidence_sha256": "f" * 64,
        "inference_evidence_sha256": "0" * 64,
        "predictions": [
            {"note_id": "private-fixture", "entities": [{"start": 2, "end": 5, "label": "ID"}]}
        ],
    }


def _record() -> Record:
    """Build a new synthetic note with emoji preceding the sensitive mock span."""
    note = Note("private-fixture", "unit-family", "🙂 ABC", (Span(2, 5, "NAME"),))
    return Record(note, "unit-group", frozenset({"name_lowercase", "unaccented_text"}))


def _parse(payload: dict[str, Any]) -> tuple[dict[str, tuple[Span, ...]], dict[str, Any]]:
    """Exercise prediction verification against a designated test, validation and manifest."""
    raw = json.dumps(payload).encode()
    manifest = {"files_sha256": {"test.jsonl": "a" * 64, "validation.jsonl": "c" * 64}}
    return parse_predictions(
        raw, sha256(raw).hexdigest(), manifest, "b" * 64, {"private-fixture": _record()}
    )


def test_binding_and_private_aggregate_output() -> None:
    """Score a wrong label over the correct masking boundary without exposing text or IDs."""
    predictions, identity = _parse(_envelope())
    report = evaluate([_record()], predictions, MIN_DRAWS)
    assert identity["method"] == "hybrid"
    assert report["overall"]["strict"]["f1"] == 0
    assert report["overall"]["partial"]["f1"] == 1
    assert report["overall"]["document_leak_rate"] == 0
    assert report["strict_document_fn_rate"] == 1
    named = report["declared_note_slices"]["name_lowercase"]
    assert named["strict"]["fn"] == 1 and named["document_leak_rate"] == 0
    assert not report["phase_m_thresholds"]["all_thresholds_met"]
    text = json.dumps({"identity": identity, **report})
    assert "private-fixture" not in text
    assert "ABC" not in text
    assert not {"predictions", "examples"} & report.keys()


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("test_sha256", "9" * 64),
        ("manifest_sha256", "9" * 64),
        ("selection_validation_sha256", "9" * 64),
        ("selected_before_test", False),
        ("observed_inference", False),
        ("model_checkpoint_sha256", None),
        ("mode", "rules"),
        ("method", "unrecognized-engine"),
        ("predictions", []),
        ("predictions", [{"note_id": "private-unexpected", "entities": []}]),
        ("predictions", [{"note_id": "private-fixture", "entities": [], "text": "private-text"}]),
        (
            "predictions",
            [
                {
                    "note_id": "private-fixture",
                    "entities": [{"start": True, "end": 5, "label": "ID"}],
                }
            ],
        ),
        (
            "predictions",
            [
                {
                    "note_id": "private-fixture",
                    "entities": [{"start": 2, "end": 5, "label": "ID", "value": "private-text"}],
                }
            ],
        ),
    ],
)
def test_reject_missing_bindings_and_sanitize_errors(field: str, replacement: object) -> None:
    """Fail closed on missing attestation, provenance mismatch or unsafe prediction rows."""
    payload = _envelope()
    payload[field] = replacement
    with pytest.raises(IntakeError) as error:
        _parse(payload)
    assert "private-" not in str(error.value)


def test_hash_and_inequality_boundaries() -> None:
    """Check content addressability and include points equality at the registered cutoffs."""
    with pytest.raises(IntakeError, match="SHA-256"):
        parse_predictions(b"{}", "0" * 64, {}, "b" * 64, {})
    by_label = {
        label: {"strict": {"recall": 0.95 if label in {"PHONE", "ID"} else 0.90, "f1": 0.80}}
        for label in GOLD_LABELS
    }
    overall = {"strict": {"f1": 0.88}, "document_leak_rate": 0.05}
    assert gate_gaps(overall, by_label)["all_thresholds_met"]
    overall["document_leak_rate"] = 0.06
    result = gate_gaps(overall, by_label)
    assert not result["all_thresholds_met"]
    assert result["criteria"][-1]["gap"] == pytest.approx(0.01)


def _rows(path: Path, values: list[dict[str, Any]]) -> None:
    """Write a private synthetic fixture with canonical UTF-8 LF endings."""
    path.write_bytes("".join(json.dumps(value) + "\n" for value in values).encode())


def _notes(prefix: str, size: int) -> list[dict[str, Any]]:
    """Make volume-only fixture records with independent train/validation/test grouping."""
    return [
        {
            "note_id": f"{prefix}-private-{index}",
            "family_id": f"{prefix}-family-{index % 3}",
            "patient_group": f"{prefix}-patient-{index}",
            "slices": list(SLICES),
            "text": f"ơ ă h m g t marker-{prefix}-{index}",
            "entities": [
                {"start": 2 * n, "end": 2 * n + 1, "label": label}
                for n, label in enumerate((*GOLD_LABELS, "NAME"))
            ],
        }
        for index in range(size)
    ]


def _run(module: str, *args: str | Path) -> dict[str, Any]:
    """Run one private CLI stage and assert its stdout contains no fixture identifiers."""
    result = subprocess.run(
        [sys.executable, "-X", "utf8", "-m", module, *map(str, args)],
        check=False,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert b"test-private" not in result.stdout and b"marker-test" not in result.stdout
    return dict(json.loads(result.stdout))


def _source(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write a fixture source in the exact unlabelled format used by preflight."""
    _rows(
        path,
        [
            {
                **{key: value for key, value in row.items() if key != "entities"},
                "source_group": "fixture",
            }
            for row in rows
        ],
    )


def test_cli_revalidates_seal_and_outputs_aggregates(tmp_path: Path) -> None:
    """Rehearse preflight through scoring and refuse changes to the sealed fixture."""
    _rows(tmp_path / "train-groups.jsonl", [{"patient_group": "train", "family_id": "train"}])
    validation = _notes("val", 100)
    _rows(tmp_path / "validation.jsonl", validation)
    validation_source = tmp_path / "validation-source.jsonl"
    _source(validation_source, validation)
    notes = _notes("test", 150)
    source = tmp_path / "source.jsonl"
    _source(source, notes)
    preflight = _run(
        "ml.phase_e_preflight", tmp_path / "train-groups.jsonl", validation_source, source
    )
    packets = tmp_path / "packets"
    _run("ml.phase_e_annotation", "prepare", source, packets, "--seed", "17")
    packet_path = tmp_path / "packet-manifest.json"
    packet = (packets / packet_path.name).read_bytes()
    packet_path.write_bytes(packet)
    assert preflight["input_sha256"]["test_source"] == json.loads(packet)["source_sha256"]
    double_ids = set(json.loads(packet)["double_note_ids"])
    observed = [{"note_id": note["note_id"], "entities": note["entities"]} for note in notes]
    a, b = tmp_path / "a-return.jsonl", tmp_path / "b-return.jsonl"
    _rows(a, observed)
    double_rows = [row for row in observed if row["note_id"] in double_ids]
    differed = double_rows[0]
    _rows(b, [{**differed, "entities": differed["entities"][1:]}, *double_rows[1:]])
    reconciled = tmp_path / "reconciled"
    receipt = _run("ml.phase_e_annotation", "reconcile", source, packet_path, a, b, reconciled)
    assert receipt["disputes"] == 1 and receipt["iaa_threshold_met"]
    adjudication = tmp_path / "adjudication.jsonl"
    _rows(adjudication, [differed])
    test_gold = tmp_path / "test.jsonl"
    _run("ml.phase_e_annotation", "finalize", reconciled, adjudication, test_gold)
    for name in ("annotations-a.jsonl", "annotations-b.jsonl"):
        (tmp_path / name).write_bytes((reconciled / name).read_bytes())
    provenance = {
        "schema_version": 1,
        "source_type": "independent_generator",
        "source_evidence_sha256": "1" * 64,
        "owner_approval_sha256": "2" * 64,
        "packet_manifest_sha256": sha256(packet).hexdigest(),
        "independent_of_detection": True,
        "human_blind_double_annotation": True,
        "annotator_a": "fixture-a",
        "annotator_b": "fixture-b",
        "adjudicator": "fixture-c",
        "participant_reviewed_count": 0,
    }
    (tmp_path / "provenance.json").write_text(json.dumps(provenance), encoding="utf-8")
    manifest = _run("ml.phase_e_intake", "seal", tmp_path)
    assert manifest["agreement"]["adjudicated_notes"] == 1
    assert _run("ml.phase_e_intake", "verify", tmp_path) == manifest
    sealed = (tmp_path / MANIFEST_NAME).read_bytes()
    envelope = {
        **_envelope(),
        "test_sha256": manifest["files_sha256"]["test.jsonl"],
        "manifest_sha256": sha256(sealed).hexdigest(),
        "selection_validation_sha256": manifest["files_sha256"]["validation.jsonl"],
        "predictions": observed,
    }
    predictions = tmp_path / "observed.json"
    output = tmp_path / "summary.json"
    raw = json.dumps(envelope).encode()
    predictions.write_bytes(raw)
    cmd = [
        sys.executable,
        "-X",
        "utf8",
        "-m",
        "ml.phase_e_evaluate",
        str(tmp_path),
        str(predictions),
        "--prediction-sha256",
        sha256(raw).hexdigest(),
        "--output",
        str(output),
    ]
    first = subprocess.run(cmd, check=False, capture_output=True)
    assert first.returncode == 0, first.stderr
    rendered = output.read_bytes()
    assert b"test-private" not in rendered and b"marker-test" not in rendered
    report = json.loads(rendered)
    assert report["review_required"]
    assert report["phase_m_thresholds"]["all_thresholds_met"]
    assert report["overall"]["strict"]["support"] == 900
    assert report["bootstrap"]["draws"] == MIN_DRAWS
    assert subprocess.run(cmd, check=False, capture_output=True).returncode != 0
    _rows(tmp_path / "test.jsonl", list(reversed(notes)))
    cmd[-1] = str(tmp_path / "must-not-exist.json")
    result = subprocess.run(cmd, check=False, capture_output=True)
    assert result.returncode != 0
    assert b"test-private" not in result.stderr and b"Traceback" not in result.stderr
    assert not Path(cmd[-1]).exists()
