# ml/scoring.py — Score exact document, span and label matches before manual review.
from collections import Counter
from collections.abc import Mapping, Sequence, Set
from typing import Literal, TypedDict

from ml.bio import GOLD_LABELS, Span
from ml.dataset import Note

ErrorKind = Literal["FP", "FN"]


class Metrics(TypedDict):
    """Metrics represents exact-match counts, ratios and gold support."""

    tp: int
    fp: int
    fn: int
    precision: float
    recall: float
    f1: float
    support: int


class ErrorExample(TypedDict):
    """ErrorExample identifies one synthetic error with its original code point slice."""

    note_id: str
    kind: ErrorKind
    label: str
    text: str
    start: int
    end: int


class Scores(TypedDict):
    """Scores summarizes predictions against a complete synthetic corpus."""

    notes: int
    gold_entities: int
    micro: Metrics
    by_label: dict[str, Metrics]
    notes_with_fn: int
    examples: list[ErrorExample]


def _metrics(tp: int, fp: int, fn: int) -> Metrics:
    """Compute P/R/F1 without rounding, returning zero for empty denominators."""
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": tp / (tp + fp) if tp + fp else 0.0,
        "recall": tp / (tp + fn) if tp + fn else 0.0,
        "f1": 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else 0.0,
        "support": tp + fn,
    }


def _examples(note: Note, kind: ErrorKind, spans: Set[Span], remaining: int) -> list[ErrorExample]:
    """Return up to the remaining number of errors of one kind in source order."""
    if remaining == 0:
        return []
    ordered = sorted(spans, key=lambda span: (span.start, span.end, span.label))
    return [
        {
            "note_id": note.note_id,
            "kind": kind,
            "label": span.label,
            "text": note.text[span.start : span.end],
            "start": span.start,
            "end": span.end,
        }
        for span in ordered[:remaining]
    ]


def score_documents(
    notes: Sequence[Note], predictions: Mapping[str, Sequence[Span]], example_limit: int = 3
) -> Scores:
    """Score every note by ID; duplicates of the same exact span count once."""
    note_ids = {note.note_id for note in notes}
    if len(note_ids) != len(notes) or note_ids != set(predictions):
        raise ValueError("Predictions must cover every unique gold note ID.")
    if example_limit < 0:
        raise ValueError("Example limit must be nonnegative.")

    tp: Counter[str] = Counter()
    fp: Counter[str] = Counter()
    fn: Counter[str] = Counter()
    false_positive_examples: list[ErrorExample] = []
    false_negative_examples: list[ErrorExample] = []
    notes_with_fn = 0
    for note in notes:
        gold = set(note.entities)
        predicted = set(predictions[note.note_id])
        if any(
            type(span.start) is not int
            or type(span.end) is not int
            or span.label not in GOLD_LABELS
            or not 0 <= span.start < span.end <= len(note.text)
            for span in gold | predicted
        ):
            raise ValueError(f"Invalid evaluation span for note {note.note_id}.")
        false_positives = predicted - gold
        false_negatives = gold - predicted
        tp.update(span.label for span in predicted & gold)
        fp.update(span.label for span in false_positives)
        fn.update(span.label for span in false_negatives)
        notes_with_fn += bool(false_negatives)
        false_positive_examples.extend(
            _examples(note, "FP", false_positives, example_limit - len(false_positive_examples))
        )
        false_negative_examples.extend(
            _examples(note, "FN", false_negatives, example_limit - len(false_negative_examples))
        )

    micro = _metrics(tp.total(), fp.total(), fn.total())
    return {
        "notes": len(notes),
        "gold_entities": micro["support"],
        "micro": micro,
        "by_label": {label: _metrics(tp[label], fp[label], fn[label]) for label in GOLD_LABELS},
        "notes_with_fn": notes_with_fn,
        "examples": false_positive_examples + false_negative_examples,
    }
