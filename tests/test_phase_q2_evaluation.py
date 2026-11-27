# tests/test_phase_q2_evaluation.py — Verify Q2 diagnostics on independent fixtures.
import pytest

from ml.bio import Span
from ml.dataset import Note
from ml.evaluation_data import load_heldout
from ml.evaluation_metrics import BOOTSTRAP_SEED, MIN_DRAWS, counts, note_has_leak, summarize
from ml.evaluation_slices import classify_span
from ml.phase_q2_archive import load_archived_mode, verify_archive
from ml.phase_q_benchmark import MODES
from ml.phase_q_dataset import DATA_DIR, load_phase_q


def test_partial_matches_use_half_credit_without_matching_twice() -> None:
    """Count wrong-type exact boundaries, half overlap, and one unmatched touching prediction."""
    gold = {Span(0, 5, "NAME"), Span(9, 12, "DOB")}
    predicted = {Span(0, 5, "ADDR"), Span(8, 10, "DOB"), Span(10, 13, "DOB"), Span(5, 8, "ID")}
    stats = counts(gold, predicted)
    assert stats.strict == 0
    assert (stats.same_boundary, stats.overlapping) == (1, 1)
    assert stats.partial_rates() == (0.375, 0.75, 0.5)
    assert counts({Span(0, 1, "ID")}, {Span(1, 2, "ID")}).overlapping == 0


def test_overlap_leak_is_distinct_from_exact_match() -> None:
    """Permit masks from different labels and count any remaining visible gold character."""
    text = "🙂 A B"
    gold = {Span(2, 5, "NAME")}
    assert not note_has_leak(text, gold, {Span(2, 3, "ID"), Span(4, 5, "ADDR")})
    assert note_has_leak(text, gold, {Span(2, 3, "NAME")})


def test_note_bootstrap_is_repeatable_and_preserves_multiplicity() -> None:
    """A hit and a missed note give separate note-resampled outcomes, including repeated draws."""
    entity = {Span(0, 3, "ID")}
    stats = [counts(entity, entity), counts(entity, set())]
    result = summarize(stats, [False, True], MIN_DRAWS, BOOTSTRAP_SEED)
    assert result == summarize(stats, [False, True], MIN_DRAWS, BOOTSTRAP_SEED)
    assert result["document_leak_rate"] == 0.5
    assert result["confidence_interval_95"] == {
        "strict": {"precision": [0.0, 1.0], "recall": [0.0, 1.0], "f1": [0.0, 1.0]},
        "partial": {"precision": [0.0, 1.0], "recall": [0.0, 1.0], "f1": [0.0, 1.0]},
        "document_leak_rate": [0.0, 1.0],
    }
    assert summarize([], [], MIN_DRAWS, BOOTSTRAP_SEED)["document_leak_rate"] is None
    with pytest.raises(ValueError, match="1.000"):
        summarize(stats, [False, True], MIN_DRAWS - 1, BOOTSTRAP_SEED)


@pytest.mark.parametrize(
    ("prefix", "value", "label", "expected"),
    [
        ("Zalo: ", "0371234567", "PHONE", "phone_in_numbering_plan"),
        ("Máy nhánh: ", "0234", "PHONE", "phone_outside_numbering_plan"),
        ("Sửa lại ngày khai sinh thứ nhất: ", "13/08/1981", "DOB", "dob_correction"),
        ("Bìa ghi năm sinh: ", "1981", "DOB", "dob_other"),
        ("Chỗ thường trú: ", "3 ngõ Gụ", "ADDR", "addr_residency_cue"),
        ("Xe ghé ", "4 ngõ Sỏi", "ADDR", "addr_no_residency_cue"),
        ("Người trình diện: ", "đoàn mai chi", "NAME", "name_lowercase"),
        ("Người trình diện: ", "ĐOÀN MAI CHI", "NAME", "name_other_case"),
    ],
)
def test_slice_classification(prefix: str, value: str, label: str, expected: str) -> None:
    """Distinguish context and surface populations independently from engine predictions."""
    span = Span(len(prefix), len(prefix + value), label)
    assert classify_span(Note("unit", "unit", prefix + value, (span,)), span) == expected


def test_historical_archive_reproduces_phase_q_rows() -> None:
    """Check the archived offset-only baseline against both complete historic aggregate rows."""
    archive = verify_archive()
    for name, notes in (("original", load_heldout(DATA_DIR)[0]), ("expanded", load_phase_q()[0])):
        for mode in MODES:
            predictions, engine = load_archived_mode(name, notes, mode, archive)
            assert set(predictions) == {note.note_id for note in notes}
            assert engine["mode"] == mode
