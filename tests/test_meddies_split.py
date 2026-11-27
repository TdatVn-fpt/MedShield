# tests/test_meddies_split.py — Verify grouping and label isolation for the Meddies review bundles.
import json
from hashlib import sha256
from typing import Any

import pytest

from ml.meddies_qa import EVAL_SOURCE, REVISION, SHARD_SHA256, TRAIN_SOURCE, text_hash
from ml.meddies_split import prepare_split
from ml.phase_e_types import SLICES, IntakeError

EVIDENCE = sha256(b"synthetic test evidence").hexdigest()


def _records(split: str, count: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Provide invented data and source assignments unrelated to the real candidate shard."""
    is_train = split == "train"
    notes = []
    assignments = []
    for index in range(count):
        note_id = f"{split}-{index:04}"
        text = f"Nội dung thử {split} {index}."
        notes.append(
            {
                "text": text,
                "info": {
                    "id": note_id,
                    "language_bucket": "vi",
                    "domain_bucket": "medical",
                    "domain_profile": "medical",
                    "split_purpose": "train",
                    "source_dataset": TRAIN_SOURCE if is_train else EVAL_SOURCE,
                    "document_type": "outpatient note" if is_train else "TRANSFER_FORM",
                },
            }
        )
        assignments.append(
            {
                "note_id": note_id,
                "text_sha256": text_hash(text),
                "patient_group": f"{split}-p-{index // 2}",
                "family_id": f"{split}-f-{index % 3}",
                "split": split,
                "slices": [] if is_train else list(SLICES),
                "evidence_ref": "fixture",
            }
        )
    return notes, assignments


def _ledger(rows: list[dict[str, Any]]) -> bytes:
    """Encode a manifest bound to the invented reviewer evidence."""
    return json.dumps(
        {
            "schema_version": 1,
            "revision": REVISION,
            "shard_sha256": SHARD_SHA256,
            "evidence_sha256": EVIDENCE,
            "reviewer": "fixture-reviewer",
            "rows": rows,
        }
    ).encode()


@pytest.fixture
def staged() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Construct the smallest three cohorts that meet pre-annotation size requirements."""
    notes, assignments = [], []
    for split, count in (("train", 2000), ("validation", 50), ("test", 150)):
        part, plan = _records(split, count)
        notes.extend(part)
        assignments.extend(plan)
    return notes, assignments


def test_split_outputs_only_groups_and_unlabelled_sources(
    staged: tuple[list[dict[str, Any]], list[dict[str, Any]]],
) -> None:
    """Produce stable packet inputs that cannot contain publisher gold or train texts."""
    notes, assignments = staged
    files, report = prepare_split(notes, _ledger(assignments), EVIDENCE)
    assert report["counts"] == {"train": 2000, "validation": 50, "test": 150}
    assert not report["locked"] and not report["evaluation_labels_used"]
    assert b'"entities"' not in files["source.jsonl"] and b'"label"' not in files["source.jsonl"]
    assert b'"text"' not in files["train-membership.jsonl"]
    assert prepare_split(list(reversed(notes)), _ledger(assignments), EVIDENCE)[0] == files


@pytest.mark.parametrize("field", ["patient_group", "family_id"])
def test_split_rejects_group_leak_across_cohorts(
    staged: tuple[list[dict[str, Any]], list[dict[str, Any]]], field: str
) -> None:
    """A family shared by one record, or a patient shared by one record, blocks splitting."""
    notes, assignments = staged
    assignments[-1][field] = assignments[0][field]
    with pytest.raises(IntakeError, match="trùng giữa"):
        prepare_split(notes, _ledger(assignments), EVIDENCE)


def test_split_rejects_stale_text_and_evidence_hashes(
    staged: tuple[list[dict[str, Any]], list[dict[str, Any]]],
) -> None:
    """The ledger cannot be reused when source bytes or the evidence record changes."""
    notes, assignments = staged
    with pytest.raises(IntakeError, match="không khớp bằng chứng"):
        prepare_split(notes, _ledger(assignments), "0" * 64)
    notes[-1]["text"] += " Đã thay đổi."
    with pytest.raises(IntakeError, match="SHA-256 văn bản"):
        prepare_split(notes, _ledger(assignments), EVIDENCE)


def test_split_reserves_even_unassigned_evaluation_candidates(
    staged: tuple[list[dict[str, Any]], list[dict[str, Any]]],
) -> None:
    """The train ledger cannot admit a duplicate of a holdout candidate marked unused."""
    notes, assignments = staged
    unassigned, _ = _records("unused", 1)
    unassigned[0]["text"] = notes[0]["text"]
    with pytest.raises(IntakeError, match="nguồn đã dành"):
        prepare_split([*notes, *unassigned], _ledger(assignments), EVIDENCE)
