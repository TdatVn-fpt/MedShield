# tests/test_meddies_intake.py — Exercise candidate quarantine and training-only label mapping.
from collections import Counter
from typing import Any

from ml.meddies_qa import EVAL_SOURCE, TRAIN_SOURCE, audit, cohort
from ml.meddies_train import birth_context, map_note


def _row(text: str, source: str, kind: str, **extra: str) -> dict[str, Any]:
    """Create a metadata-only fixture that resembles a single independent publisher document."""
    return {
        "text": text,
        "info": {
            "domain_profile": "medical",
            "domain_bucket": "medical",
            "language_bucket": "vi",
            "source_dataset": source,
            "document_type": kind,
            "split_purpose": "train",
            "original_id": "opaque-row",
            "scenario": "fixture",
            "source": "fixture",
            **extra,
        },
    }


def test_evaluation_cohort_quarantines_matching_training_text() -> None:
    """Exclude repeated evaluation text from provisional train and preserve lineage flags."""
    reserved = _row("Mẫu chung", EVAL_SOURCE, "TRANSFER_FORM")
    conflict = _row("Mẫu chung", TRAIN_SOURCE, "outpatient note")
    train = _row("Mẫu khám", TRAIN_SOURCE, "outpatient note")
    non_medical = _row("Nhật ký kỹ thuật", TRAIN_SOURCE, "API error report")
    assert cohort(non_medical) == "medical_metadata_insufficient"
    result = audit([reserved, conflict, reserved, train, non_medical])
    assert result["cohorts"]["evaluation_candidate"]["count"] == 1
    assert result["cohorts"]["provisional_train"]["count"] == 1
    assert result["exact_text_exclusions"] == {"evaluation_candidate": 1, "provisional_train": 1}
    assert (
        not result["numeric_gate_met"] and not result["patient_and_family_disjointness_verified"]
    )


def test_dob_uses_nearby_birth_context_and_original_unicode_offsets() -> None:
    """Retain DOB by its own cue and reject a clinical date and school homonym."""
    text = "🙂 Năm sinh: 1978; ngày khám 05/09/2020. Học sinh 2012 đến khám."
    assert birth_context(text, text.index("1978"), text.index("1978") + 4)
    for value in ("05/09/2020", "2012"):
        start = text.index(value)
        assert not birth_context(text, start, start + len(value))


def test_mapper_reports_out_of_scope_invalid_and_conflicting_labels() -> None:
    """Preserve valid original offsets and discard ambiguous overlaps."""
    text = "🙂 tên Lê Lan. DOB 1990. Hẹn 2030-01-01. aa@example.test"

    def item(value: str, category: str) -> dict[str, Any]:
        """Create an exact interval for the invented training sample."""
        offset = text.index(value)
        return {"category": category, "start": offset, "end": offset + len(value), "text": value}

    a, b = Counter[str](), Counter[str]()
    result = map_note(
        text,
        [
            item("Lê Lan", "human_name"),
            item("Lan", "address"),
            item("1990", "date"),
            item("2030-01-01", "date"),
            {**item("1990", "id_number"), "text": "9999"},
            item("aa@example.test", "email_address"),
        ],
        a,
        b,
    )
    assert result == [{"start": text.index("1990"), "end": text.index("1990") + 4, "label": "DOB"}]
    assert dict(b) == {
        "date_without_birth_cue": 1,
        "invalid_offset_or_value": 1,
        "outside_scope": 1,
        "overlapping_span": 2,
    }
