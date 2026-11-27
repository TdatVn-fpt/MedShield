# ml/phase_q2_benchmark.py — Compare pre-Q2 and current inference with independent diagnostics.
import json
from argparse import ArgumentParser
from collections import Counter
from collections.abc import Mapping, Sequence, Set
from hashlib import sha256
from pathlib import Path
from typing import Any

from apps.api.services.analysis import analyze_text
from ml.bio import GOLD_LABELS, Span
from ml.dataset import Note
from ml.evaluation_data import load_heldout
from ml.evaluation_metrics import BOOTSTRAP_SEED, MIN_DRAWS, counts, note_has_leak, summarize
from ml.evaluation_slices import SLICE_LABELS, classify_span
from ml.phase_q2_archive import (
    ARCHIVE_DIGEST,
    PRIOR_REPORT,
    SNAPSHOT_SOURCES,
    capture,
    load_archived_mode,
    verify_archive,
)
from ml.phase_q_benchmark import FROZEN, MODES, ROOT, _cause, _verify_frozen
from ml.phase_q_dataset import DATA_DIR, load_phase_q
from ml.scoring import score_documents

CANDIDATE_SOURCES = (*SNAPSHOT_SOURCES, "apps/api/adapters/vi_boundaries.py")


def _candidate_hashes() -> dict[str, str]:
    """Identify the evaluated candidate sources using LF-canonical SHA-256."""
    return {
        path: sha256((ROOT / path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        for path in CANDIDATE_SOURCES
    }


def _error_report(
    notes: Sequence[Note],
    predictions: Mapping[str, Sequence[Span]],
    populations: Mapping[str, Mapping[Span, str | None]],
) -> dict[str, Any]:
    """Count strict errors and choose up to five synthetic examples per kind across cohorts."""
    totals: dict[str, Counter[str]] = {"FP": Counter(), "FN": Counter()}
    by_slice: dict[str, Counter[str]] = {"FP": Counter(), "FN": Counter()}
    best: dict[str, list[dict[str, Any]]] = {"FP": [], "FN": []}
    remaining: dict[str, list[dict[str, Any]]] = {"FP": [], "FN": []}
    groups: set[tuple[str, str, str, str]] = set()
    for note in notes:
        gold, predicted = set(note.entities), set(predictions[note.note_id])
        for kind, source, other in (("FP", predicted, gold), ("FN", gold, predicted)):
            for span in sorted(
                source - other, key=lambda item: (item.start, item.end, item.label)
            ):
                cause = _cause(span, other)
                cohort = populations[note.note_id][span] or "id_all"
                totals[kind][cause] += 1
                by_slice[kind][cohort] += 1
                record = {
                    "note_id": note.note_id,
                    "family_id": note.family_id,
                    "label": span.label,
                    "start": span.start,
                    "end": span.end,
                    "text": note.text[span.start : span.end],
                    "slice": cohort,
                    "cause": cause,
                }
                key = kind, span.label, cohort, cause
                if key in groups:
                    remaining[kind].append(record)
                else:
                    groups.add(key)
                    best[kind].append(record)
    return {
        "counts_by_cause": totals,
        "counts_by_slice": by_slice,
        "examples": {kind: (best[kind] + remaining[kind])[:5] for kind in totals},
    }


def _selected(
    spans: Set[Span], label: str | None, population: str | None, classes: Mapping[Span, str | None]
) -> set[Span]:
    """Choose all spans, a label, or an independently classified diagnostic slice."""
    return {
        span
        for span in spans
        if (label is None or span.label == label)
        and (population is None or classes[span] == population)
    }


def _metric_group(
    notes: Sequence[Note],
    predictions: Mapping[str, Sequence[Span]],
    classes: Mapping[str, Mapping[Span, str | None]],
    draws: int,
    label: str | None = None,
    population: str | None = None,
) -> dict[str, Any]:
    """Compare gold and predictions for one scope, always testing leak against full masks."""
    rows, leaked = [], []
    for note in notes:
        classified = classes[note.note_id]
        masks = set(predictions[note.note_id])
        gold = _selected(set(note.entities), label, population, classified)
        predicted = _selected(masks, label, population, classified)
        if population is not None and not (gold or predicted):
            continue
        rows.append(counts(gold, predicted))
        leaked.append(note_has_leak(note.text, gold, masks))
    return summarize(rows, leaked, draws, BOOTSTRAP_SEED)


def measure(
    notes: Sequence[Note],
    predictions: Mapping[str, Sequence[Span]],
    engine: dict[str, Any],
    draws: int,
) -> dict[str, Any]:
    """Use the frozen scorer for strict and append partial, leak, confidence and slice results."""
    strict = score_documents(notes, predictions, example_limit=0)
    classes = {
        note.note_id: {
            span: classify_span(note, span)
            for span in set(note.entities) | set(predictions[note.note_id])
        }
        for note in notes
    }
    overall = _metric_group(notes, predictions, classes, draws)
    by_label = {
        label: _metric_group(notes, predictions, classes, draws, label) for label in GOLD_LABELS
    }
    if overall["strict"] != strict["micro"] or any(
        summary["strict"] != strict["by_label"][label] for label, summary in by_label.items()
    ):
        raise ValueError("Số đếm dùng cho bootstrap không khớp scorer strict đã đóng băng.")
    return {
        "engine": engine,
        "overall": {**overall, "strict": strict["micro"]},
        "strict_notes_with_fn": strict["notes_with_fn"],
        "strict_document_fn_rate": strict["notes_with_fn"] / len(notes),
        "by_label": {
            label: {**summary, "strict": strict["by_label"][label]}
            for label, summary in by_label.items()
        },
        "slices": {
            name: _metric_group(notes, predictions, classes, draws, label, name)
            for name, label in SLICE_LABELS.items()
        },
        "errors": _error_report(notes, predictions, classes),
    }


def _check_gates(sets: Mapping[str, Any]) -> dict[str, Any]:
    """Assess only Q2 regression checks with the historical comparison denominators."""
    before_initial_q = json.loads(PRIOR_REPORT.read_bytes())["sets"]
    checks: list[dict[str, Any]] = []
    for set_name, versions in sets.items():
        before = versions["versions"]["before"]
        after = versions["versions"]["after"]
        initial_q = next(
            item
            for item in before_initial_q[set_name]["versions"]["before"]
            if item["method"] == "hybrid"
        )
        value = after["hybrid"]["by_label"]["ADDR"]["strict"]["f1"]
        target = initial_q["by_label"]["ADDR"]["f1"]
        checks.append(
            {
                "check": f"{set_name}.hybrid.ADDR.strict_f1",
                "value": value,
                "minimum": target,
                "met": value >= target,
            }
        )
        if set_name == "original":
            for mode in ("rules", "hybrid"):
                for label in ("DOB", "PHONE"):
                    value = after[mode]["by_label"][label]["strict"]["recall"]
                    checks.append(
                        {
                            "check": f"{set_name}.{mode}.{label}.strict_recall",
                            "value": value,
                            "strictly_greater_than": 0,
                            "met": value > 0,
                        }
                    )
        else:
            for mode in MODES:
                value = (
                    after[mode]["overall"]["strict"]["f1"]
                    - before[mode]["overall"]["strict"]["f1"]
                )
                checks.append(
                    {
                        "check": f"{set_name}.{mode}.micro_f1_change_from_phase_q",
                        "value": value,
                        "minimum": -0.02,
                        "met": value >= -0.02,
                    }
                )
    return {
        "kind": "regression_only",
        "all_criteria_met": all(row["met"] for row in checks),
        "criteria": checks,
    }


def main() -> None:
    """Measure both frozen historical datasets and write an immutable, reproducible JSON result."""
    parser = ArgumentParser(
        description="Đo Phase Q2: strict, partial, bootstrap, lát cắt và PHI sót."
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--draws", type=int, default=MIN_DRAWS)
    parser.add_argument("--baseline-only", action="store_true")
    args = parser.parse_args()
    if args.draws < MIN_DRAWS:
        parser.error("--draws phải từ 1000 trở lên.")
    _verify_frozen()
    archive = verify_archive()
    candidate_sources = None if args.baseline_only else _candidate_hashes()
    sets: dict[str, Any] = {}
    for set_name, (notes, manifest) in {
        "original": load_heldout(DATA_DIR),
        "expanded": load_phase_q(),
    }.items():
        before, after = {}, {}
        for mode in MODES:
            archived, historical_engine = load_archived_mode(set_name, notes, mode, archive)
            before[mode] = measure(notes, archived, historical_engine, args.draws)
            if not args.baseline_only:
                current, current_engine = capture(notes, mode, analyze_text)
                if current_engine.get("model_revision") != historical_engine.get("model_revision"):
                    raise ValueError("Phase Q2 yêu cầu giữ nguyên revision mô hình CRF.")
                after[mode] = measure(notes, current, current_engine, args.draws)
        sets[set_name] = {
            "use": "historical_reference" if set_name == "original" else "regression_only",
            "manifest": manifest,
            "versions": {"before": before}
            if args.baseline_only
            else {"before": before, "after": after},
        }
    if candidate_sources is not None and candidate_sources != _candidate_hashes():
        raise ValueError("Mã nguồn Q2 thay đổi trong lúc đang đánh giá.")
    report = {
        "schema_version": 1,
        "frozen_sha256": FROZEN,
        "phase_q_baseline": {"archive_sha256": ARCHIVE_DIGEST, "source_sha256": SNAPSHOT_SOURCES},
        "q2_sources_sha256": candidate_sources,
        "bootstrap": {
            "resample_unit": "note",
            "draws": args.draws,
            "seed": BOOTSTRAP_SEED,
            "confidence": 0.95,
        },
        "partial": "boundary_exact_1_nonempty_overlap_0.5_ignores_label_within_scope",
        "document_leak": "any_non_whitespace_gold_code_point_outside_mask_union",
        "slice_document_denominator": "notes_with_gold_or_predicted_span_in_slice",
        "sets": sets,
        "q2_regression_criteria": None if args.baseline_only else _check_gates(sets),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(args.output)


if __name__ == "__main__":
    main()
