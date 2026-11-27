# ml/meddies_agreement.py — Bootstrap whole notes and check provisional Meddies support.
from collections import Counter
from random import Random
from statistics import quantiles
from typing import Any

from ml.bio import GOLD_LABELS
from ml.dataset import Note
from ml.evaluation_metrics import BOOTSTRAP_SEED, MIN_DRAWS


def _interval(values: list[float]) -> list[float]:
    """Return the inclusive 2.5th and 97.5th percentiles for bootstrap samples."""
    points = quantiles(values, n=40, method="inclusive")
    return [points[0], points[-1]]


def agreement_intervals(a: dict[str, Note], b: dict[str, Note]) -> dict[str, Any]:
    """Estimate strict F1 and disagreement intervals by resampling paired whole notes."""
    labels = sorted(GOLD_LABELS)
    counts = []
    disagreements = []
    for key in sorted(a):
        left, right = set(a[key].entities), set(b[key].entities)
        matches = Counter(span.label for span in left & right)
        totals = Counter(span.label for span in [*left, *right])
        counts.append(
            [(matches.total(), totals.total()), *[(matches[k], totals[k]) for k in labels]]
        )
        disagreements.append(left != right)
    metrics = ["micro", *labels]
    draws: dict[str, list[float]] = {metric: [] for metric in metrics}
    disagreement_samples: list[float] = []
    rng = Random(BOOTSTRAP_SEED)
    for _ in range(MIN_DRAWS):
        indices = rng.choices(range(len(counts)), k=len(counts))
        for column, metric in enumerate(metrics):
            matches_sum = sum(counts[index][column][0] for index in indices)
            total_sum = sum(counts[index][column][1] for index in indices)
            draws[metric].append(2 * matches_sum / total_sum if total_sum else 0.0)
        disagreement_samples.append(
            sum(disagreements[index] for index in indices) / len(indices) if indices else 0.0
        )
    return {
        "draws": MIN_DRAWS,
        "seed": BOOTSTRAP_SEED,
        "strict_f1": {metric: _interval(values) for metric, values in draws.items()},
        "disagreement_rate": _interval(disagreement_samples),
    }


def support_threshold(split: str, notes: int, labels: dict[str, int]) -> bool:
    """Apply registered support requirements to one split's counts."""
    if split == "validation":
        return all(labels[label] >= 100 for label in GOLD_LABELS)
    return (
        150 <= notes <= 200
        and sum(labels.values()) >= 800
        and all(labels[label] > 0 for label in GOLD_LABELS)
    )
