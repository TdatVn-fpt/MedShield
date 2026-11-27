# tests/test_phase_q_benchmark.py — Test holdout reproducibility and exact-error explanations.
from collections import Counter
from pathlib import Path

from ml.bio import Span
from ml.dataset import Note
from ml.phase_q_benchmark import _diagnose, _verify_frozen
from ml.phase_q_dataset import CORPUS, DATA_DIR, MANIFEST, generate, load_phase_q


def test_phase_q_rebuild_matches_the_frozen_corpus(tmp_path: Path) -> None:
    """Reproduce every byte and confirm independent support and zero participant review."""
    _verify_frozen()
    generate(tmp_path)
    for filename in (CORPUS, MANIFEST):
        assert (tmp_path / filename).read_bytes() == (DATA_DIR / filename).read_bytes()
    notes, manifest = load_phase_q(tmp_path)
    assert len(notes) == 150
    assert len({note.family_id for note in notes}) == 15
    assert sum(not note.entities for note in notes) == 20
    assert manifest["participant_reviewed_count"] == 0
    assert Counter(span.label for note in notes for span in note.entities) == {
        "NAME": 170,
        "DOB": 80,
        "PHONE": 120,
        "ID": 100,
        "ADDR": 90,
    }


def test_phase_q_explanations_cover_all_strict_error_shapes() -> None:
    """Distinguish absent spans, boundary shifts, wrong labels and combined errors."""
    notes = [
        Note(
            "demo",
            "synthetic",
            "abcdefghijklmnopqrst",
            (Span(0, 3, "NAME"), Span(5, 8, "DOB"), Span(10, 13, "ID"), Span(15, 16, "ADDR")),
        )
    ]
    predictions = {
        "demo": [Span(0, 2, "NAME"), Span(5, 8, "ID"), Span(11, 13, "PHONE"), Span(18, 19, "NAME")]
    }
    counts, causes = _diagnose(notes, predictions)
    expected = {"wrong_boundary": 1, "wrong_label": 1, "boundary_and_label": 1, "no_overlap": 1}
    assert counts == {"FP": expected, "FN": expected}
    assert causes["demo", "FP", 0, 2] == "wrong_boundary"
    assert causes["demo", "FN", 5, 8] == "wrong_label"
