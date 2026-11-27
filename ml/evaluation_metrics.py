# ml/evaluation_metrics.py — Measure partial matches and bootstrap confidence by note.
from collections.abc import Sequence
from dataclasses import dataclass
from random import Random
from statistics import quantiles

from ml.bio import Span

BOOTSTRAP_SEED = 20261125
MIN_DRAWS = 1000


@dataclass(frozen=True, slots=True)
class Counts:
    """Store additive gold, prediction, exact and partial counts for one note or corpus."""

    gold: int
    predicted: int
    strict: int
    same_boundary: int
    overlapping: int

    def strict_rates(self) -> tuple[float, float, float]:
        """Return exact precision, recall and F1 with the frozen scorer's empty convention."""
        return _rates(self.strict, self.predicted, self.gold)

    def partial_rates(self) -> tuple[float, float, float]:
        """Return span-only partial precision, recall and F1 with half overlap credit."""
        return _rates(self.same_boundary + 0.5 * self.overlapping, self.predicted, self.gold)


def _rates(credit: float, predicted: int, gold: int) -> tuple[float, float, float]:
    """Convert exact or fractional matching counts to precision, recall and F1."""
    return (
        credit / predicted if predicted else 0.0,
        credit / gold if gold else 0.0,
        2 * credit / (predicted + gold) if predicted + gold else 0.0,
    )


def _partial(gold: set[Span], predicted: set[Span]) -> tuple[int, int]:
    """Match one-to-one by boundaries ignoring type, preferring exact per prediction.

    Pairs are considered in source-offset order. Any nonempty code-point overlap
    earns half credit when the boundaries differ. Touching half-open spans do not overlap.
    """
    remaining = sorted(gold, key=lambda item: (item.start, item.end, item.label))
    correct = partial = 0
    for span in sorted(predicted, key=lambda item: (item.start, item.end, item.label)):
        exact_index = first_overlap = None
        for index, candidate in enumerate(remaining):
            if candidate.start >= span.end:
                break
            if candidate.end <= span.start:
                continue
            if (span.start, span.end) == (candidate.start, candidate.end):
                exact_index = index
                break
            if first_overlap is None:
                first_overlap = index
        if exact_index is not None:
            correct += 1
            remaining.pop(exact_index)
        elif first_overlap is not None:
            partial += 1
            remaining.pop(first_overlap)
    return correct, partial


def counts(gold: set[Span], predicted: set[Span]) -> Counts:
    """Compute one note's strict and partial additive counts."""
    exact, partial = _partial(gold, predicted)
    return Counts(len(gold), len(predicted), len(gold & predicted), exact, partial)


def note_has_leak(text: str, gold: set[Span], applied_masks: set[Span]) -> bool:
    """Report any nonspace gold code point that remains uncovered by the union of masks."""
    covered = bytearray(len(text))
    for span in applied_masks:
        covered[span.start : span.end] = b"\x01" * (span.end - span.start)
    return any(
        not covered[index] and not text[index].isspace()
        for span in gold
        for index in range(span.start, span.end)
    )


def _sum_counts(notes: Sequence[Counts], indices: Sequence[int]) -> Counts:
    """Aggregate note counts with multiplicity so bootstrap draws may repeat a document."""
    gold = predicted = strict = same_boundary = overlapping = 0
    for index in indices:
        row = notes[index]
        gold += row.gold
        predicted += row.predicted
        strict += row.strict
        same_boundary += row.same_boundary
        overlapping += row.overlapping
    return Counts(gold, predicted, strict, same_boundary, overlapping)


def _percentile(values: list[float]) -> list[float]:
    """Return the 2.5th and 97.5th inclusive percentile endpoints."""
    ranked = quantiles(values, n=40, method="inclusive")
    return [ranked[0], ranked[-1]]


def summarize(
    stats: Sequence[Counts], leaks: Sequence[bool], draws: int, seed: int
) -> dict[str, object]:
    """Aggregate corpus counts and seeded 95% percentile CIs from whole-note resampling."""
    if draws < MIN_DRAWS or len(stats) != len(leaks):
        raise ValueError("Bootstrap cần tối thiểu 1.000 lượt và cùng số ghi chú.")
    num_notes = len(stats)
    total = _sum_counts(stats, range(num_notes))
    strict = total.strict_rates()
    partial = total.partial_rates()
    rate_keys = ("precision", "recall", "f1")
    strict_samples: list[tuple[float, float, float]] = []
    partial_samples: list[tuple[float, float, float]] = []
    leak_samples: list[float] = []
    rng = Random(seed)
    if num_notes:
        for _ in range(draws):
            selected = rng.choices(range(num_notes), k=num_notes)
            resampled = _sum_counts(stats, selected)
            strict_samples.append(resampled.strict_rates())
            partial_samples.append(resampled.partial_rates())
            leak_samples.append(sum(leaks[index] for index in selected) / num_notes)
    return {
        "notes": num_notes,
        "strict": {
            "tp": total.strict,
            "fp": total.predicted - total.strict,
            "fn": total.gold - total.strict,
            "support": total.gold,
            **dict(zip(rate_keys, strict, strict=True)),
        },
        "partial": {
            "exact_boundary": total.same_boundary,
            "overlapping": total.overlapping,
            "spurious": total.predicted - total.same_boundary - total.overlapping,
            "missed": total.gold - total.same_boundary - total.overlapping,
            "support": total.gold,
            **dict(zip(rate_keys, partial, strict=True)),
        },
        "notes_with_unmasked_gold": sum(leaks),
        "document_leak_rate": sum(leaks) / num_notes if num_notes else None,
        "confidence_interval_95": {
            "strict": {
                key: _percentile([values[index] for values in strict_samples])
                for index, key in enumerate(rate_keys)
            }
            if strict_samples
            else None,
            "partial": {
                key: _percentile([values[index] for values in partial_samples])
                for index, key in enumerate(rate_keys)
            }
            if partial_samples
            else None,
            "document_leak_rate": _percentile(leak_samples) if leak_samples else None,
        },
    }
