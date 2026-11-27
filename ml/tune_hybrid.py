# ml/tune_hybrid.py — Diagnose possible hybrid score floors on development notes.
import json
from itertools import product
from typing import cast

from apps.api.adapters import ner, rules
from apps.api.adapters.vi_boundaries import refine
from apps.api.adapters.vi_names_places import repeat_names
from apps.api.schemas import Entity, Label
from apps.api.services import hybrid
from ml.bio import GOLD_LABELS, Span
from ml.dataset import Note, load_dataset
from ml.generate_data import DEFAULT_DATA_DIR
from ml.scoring import Metrics, score_documents

GRID = (0.0, 0.75, 0.9)


def predict(
    note: Note, rules_spans: list[Entity], crf_spans: list[Entity], floors: dict[Label, float]
) -> list[Span]:
    """Score the full hybrid policy, including exact name repeats, on one development note."""
    chosen = hybrid.combine(
        [item for item in rules_spans if item.score >= floors[item.label]],
        [item for item in crf_spans if item.score >= floors[item.label]],
    )
    repeated = [item for item in repeat_names(note.text, chosen) if item.score >= floors["NAME"]]
    final = rules.resolve_overlaps(chosen + repeated, hybrid.priority) if repeated else chosen
    return [Span(entity.start, entity.end, entity.label) for entity in final]


def f2(metrics: Metrics) -> float:
    """Compute recall-weighted F2 from exact counts without modifying the strict scorer."""
    tp, fp, fn = metrics["tp"], metrics["fp"], metrics["fn"]
    denominator = 5 * tp + fp + 4 * fn
    return 5 * tp / denominator if denominator else 0.0


def main() -> None:
    """Enumerate per-label floors and print the best validation configuration and identity."""
    data = load_dataset(DEFAULT_DATA_DIR)
    model = ner.available_model()
    if model is None:
        raise RuntimeError("Không nạp được mô hình CRF.")
    cached = [
        (
            note,
            rules.vietnamese_candidates(note.text),
            refine(note.text, ner.recognize(note.text, model)),
        )
        for note in data.validation
    ]
    best_rank: tuple[float, float, float] | None = None
    best = {}
    labels = [cast(Label, label) for label in GOLD_LABELS]
    for values in product(GRID, repeat=len(labels)):
        floors = dict(zip(labels, values, strict=True))
        scored = score_documents(
            data.validation,
            {note.note_id: predict(note, rule, crf, floors) for note, rule, crf in cached},
            example_limit=0,
        )
        supported = [item for item in scored["by_label"].values() if item["support"]]
        rank = (
            sum(f2(item) for item in supported) / len(supported),
            f2(scored["micro"]),
            -sum(values),
        )
        if best_rank is None or rank > best_rank:
            best_rank = rank
            best = {
                "thresholds": floors,
                "validation_notes": len(data.validation),
                "validation_sha256": data.split_sha256["validation"],
                "model_revision": model.revision,
                "grid": GRID,
                "selection": "macro_F2_then_micro_F2_then_lowest_thresholds",
                "policy": "diagnostic grid only; scores are uncalibrated",
                "macro_f2": rank[0],
                "micro_f2": rank[1],
                "scores": scored,
            }
    support = {
        label: {
            "spans": sum(
                span.label == label for note in data.validation for span in note.entities
            ),
            "families": len(
                {
                    note.family_id
                    for note in data.validation
                    if any(span.label == label for span in note.entities)
                }
            ),
        }
        for label in labels
    }
    best["validation_support"] = support
    best["minimum_support_met"] = all(
        item["spans"] >= 100 and item["families"] >= 3 for item in support.values()
    )
    best["calibration_applied"] = False
    best["active_floors"] = None
    print(json.dumps(best, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
