# tests/test_phase_e_preflight.py — Verify source separation before annotation on invented notes.
import json
import subprocess
import sys
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from ml.phase_e_preflight import audit_sources
from ml.phase_e_types import SLICES, IntakeError


def _jsonl(rows: list[dict[str, Any]]) -> bytes:
    """Serialize invented source rows using the private LF JSONL format."""
    return "".join(json.dumps(row) + "\n" for row in rows).encode()


def _source(split: str, total: int) -> list[dict[str, Any]]:
    """Generate distinct fictional note texts, group IDs and declared slices for protocol tests."""
    return [
        {
            "note_id": f"opaque-{split}-{i}",
            "patient_group": f"pat-{split}-{i}",
            "family_id": f"fam-{split}-{i % 3}",
            "source_group": f"source-{split}",
            "text": f"🧭 Mẫu kiểm thử {split} {i}",
            "slices": [list(SLICES)[i]] if i < len(SLICES) else [],
        }
        for i in range(total)
    ]


TRAIN = _jsonl([{"patient_group": "pat-train-0", "family_id": "fam-train-0"}])


def test_preflight_returns_hashes_and_coverage_without_note_or_group_values(
    tmp_path: Path,
) -> None:
    """Exercise the real CLI and verify its output contains only counts and source digests."""
    val, holdout = _jsonl(_source("val", 10)), _jsonl(_source("test", 150))
    paths = [tmp_path / name for name in ("train.jsonl", "validation.jsonl", "source.jsonl")]
    for path, raw in zip(paths, (TRAIN, val, holdout), strict=True):
        path.write_bytes(raw)
    result = subprocess.run(
        [sys.executable, "-X", "utf8", "-m", "ml.phase_e_preflight", *map(str, paths)],
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert b"opaque-test-" not in result.stdout and b"fam-val-" not in result.stdout
    report = json.loads(result.stdout)
    assert report["input_sha256"]["test_source"] == sha256(holdout).hexdigest()
    assert report["stage"] == "before_annotation" and report["test"]["notes"] == 150
    assert report["test"]["declared_slice_notes"] == dict.fromkeys(SLICES, 1)


@pytest.mark.parametrize("field", ["patient_group", "family_id", "text", "note_id"])
def test_rejects_overlap_even_when_other_fields_differ(field: str) -> None:
    """Reject both grouping collisions and repeated documents with otherwise different IDs."""
    validation, heldout = _source("val", 10), _source("test", 150)
    heldout[-1][field] = validation[0][field]
    with pytest.raises(IntakeError, match="trùng giữa"):
        audit_sources(TRAIN, _jsonl(validation), _jsonl(heldout))


def test_rejects_unviable_source_sizes_and_missing_declared_slice() -> None:
    """Catch insufficient family diversity and slice coverage before sending packets."""
    heldout = _source("test", 150)
    with pytest.raises(IntakeError, match="ít nhất 3 họ"):
        audit_sources(TRAIN, _jsonl(_source("val", 2)), _jsonl(heldout))
    validation = _jsonl(_source("val", 10))
    with pytest.raises(IntakeError, match="ít nhất 150"):
        audit_sources(TRAIN, validation, _jsonl(heldout[:-1]))
    heldout[0]["slices"] = []
    with pytest.raises(IntakeError, match="đủ các lát"):
        audit_sources(TRAIN, validation, _jsonl(heldout))
