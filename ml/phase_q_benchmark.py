# ml/phase_q_benchmark.py — Compare Phase Q against the original engine with the frozen scorer.
import json
from argparse import ArgumentParser
from collections import Counter
from collections.abc import Callable, Sequence
from hashlib import sha256
from pathlib import Path
from subprocess import check_output
from types import ModuleType
from typing import Any, cast

from apps.api.schemas import AnalyzeRequest, AnalyzeResponse, Mode
from apps.api.services.analysis import analyze_text
from ml.bio import Span
from ml.dataset import Note
from ml.evaluation_data import TEST_FILENAME, TEST_MANIFEST_FILENAME, load_heldout
from ml.phase_q_dataset import DATA_DIR, load_phase_q
from ml.scoring import score_documents

ROOT = DATA_DIR.parent
BASELINE_REVISION = "773cead6eea623a345e1e1fa6b5732a8b2b6ae77"
BASELINE_MODEL_REVISION = "sha256:8f0ee850c659b7c13d23280cad1a7c88c1fd051dc462ca5188810d392a7bce3f"
FROZEN = {
    "ml/scoring.py": "6f3f4e8b4c242c6f418003cb192a1dba967ad3161b0957a89adc9c3e5ab512c0",
    f"data/{TEST_FILENAME}": "ad2dce2254e1eac809df51f5a827f64bfdb425babf1ca56cb5db87f7dea9bb96",
    f"data/{TEST_MANIFEST_FILENAME}": (
        "0b666c65fe50e80c6bbe478f9fbad82aba44ab91205962836b63e3a4db6aa91a"
    ),
    "data/phase-q-test.jsonl": "c5b34eea0816fbe3c57ecf070e23430bec1c008e971d8c816853bb497b589bc0",
    "data/phase-q-test-manifest.json": (
        "0c8bd00ef45b01a6dcb6c8aebc5b307735ff1f5205d8a43527a5f82b613d6bbd"
    ),
}
MODES: tuple[Mode, ...] = ("rules", "ner", "hybrid")
Analyzer = Callable[[AnalyzeRequest], AnalyzeResponse]


def _digest(path: Path) -> str:
    """Hash a text file using LF between physical lines, without touching JSON string contents."""
    return sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _verify_frozen() -> None:
    """Reject changes to the frozen scorer, held-out sets and their manifests."""
    for relative, expected in FROZEN.items():
        if _digest(ROOT / relative) != expected:
            raise ValueError(f"Phase Q SHA-256 mismatch: {relative}")


def _baseline_module(relative: str) -> ModuleType:
    """Load the exact trusted repository revision directly from local Git."""
    source = check_output(["git", "show", f"{BASELINE_REVISION}:{relative}"], cwd=ROOT)
    module = ModuleType("phase_q_baseline")
    exec(compile(source, relative, "exec"), module.__dict__)
    return module


def _baseline_analyzer() -> Analyzer:
    """Restore original analysis, adapters and CRF inference without a second checkout."""
    analysis = _baseline_module("apps/api/services/analysis.py")
    analysis.__dict__["rules"] = _baseline_module("apps/api/adapters/rules.py")
    analysis.__dict__["ner"] = _baseline_module("apps/api/adapters/ner.py")
    return cast(Analyzer, analysis.analyze_text)


def _cause(span: Span, alternatives: set[Span]) -> str:
    """Classify a strict error by its best geometric match, independently of exact scoring."""
    if any(span.start == other.start and span.end == other.end for other in alternatives):
        return "wrong_label"
    intersects = {
        other for other in alternatives if span.start < other.end and other.start < span.end
    }
    if any(other.label == span.label for other in intersects):
        return "wrong_boundary"
    return "boundary_and_label" if intersects else "no_overlap"


def _diagnose(
    notes: Sequence[Note], predictions: dict[str, list[Span]]
) -> tuple[dict[str, dict[str, int]], dict[tuple[str, str, int, int], str]]:
    """Return complete error counts and attach geometric causes to displayed scorer examples."""
    counts: dict[str, dict[str, int]] = {}
    causes: dict[tuple[str, str, int, int], str] = {}
    for kind in ("FP", "FN"):
        counts_by_cause: Counter[str] = Counter()
        for note in notes:
            gold, predicted = set(note.entities), set(predictions[note.note_id])
            first, second = (predicted, gold) if kind == "FP" else (gold, predicted)
            for span in first - second:
                cause = _cause(span, second)
                counts_by_cause[cause] += 1
                causes[note.note_id, kind, span.start, span.end] = cause
        counts[kind] = dict(sorted(counts_by_cause.items()))
    return counts, causes


def _measure(notes: Sequence[Note], mode: Mode, analyzer: Analyzer) -> dict[str, Any]:
    """Score real service detections and preserve engine identity and representative failures."""
    predictions: dict[str, list[Span]] = {}
    engine = None
    for note in notes:
        result = analyzer(AnalyzeRequest(text=note.text, mode=mode, language="vi"))
        if engine is not None and result.engine != engine:
            raise ValueError(f"Engine identity changed in {mode}.")
        engine = result.engine
        predictions[note.note_id] = [
            Span(entity.start, entity.end, entity.label) for entity in result.entities
        ]
    if engine is None or engine.status != "available":
        raise ValueError(f"No available engine in {mode}.")
    if mode != "rules" and engine.model_revision != BASELINE_MODEL_REVISION:
        raise ValueError(f"Phase Q requires the original CRF model in {mode}.")
    scores = score_documents(notes, predictions, example_limit=5)
    counts, causes = _diagnose(notes, predictions)
    return {
        "method": mode,
        "unit": "exact_span_label",
        "engine": engine.model_dump(exclude_none=True),
        **scores,
        "diagnostic_counts": counts,
        "examples": [
            {
                **example,
                "cause": causes[
                    example["note_id"], example["kind"], example["start"], example["end"]
                ],
            }
            for example in scores["examples"]
        ],
    }


def main() -> None:
    """Write comparable versions for both independent held-out sets without changing artifacts."""
    parser = ArgumentParser(description="Đo Phase Q trên tập khóa gốc và tập mở rộng.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--baseline", action="store_true", help="Chỉ chạy code gốc đã ghi commit.")
    args = parser.parse_args()
    _verify_frozen()
    original_notes, original_manifest = load_heldout(DATA_DIR)
    expanded_notes, expanded_manifest = load_phase_q()
    analyzers = {"before": _baseline_analyzer()}
    if not args.baseline:
        analyzers["after"] = analyze_text
    result: dict[str, Any] = {
        "schema_version": 1,
        "baseline_revision": BASELINE_REVISION,
        "frozen_sha256": FROZEN,
        "sets": {},
    }
    for key, notes, manifest in (
        ("original", original_notes, original_manifest),
        ("expanded", expanded_notes, expanded_manifest),
    ):
        result["sets"][key] = {
            "manifest": manifest,
            "versions": {
                version: [_measure(notes, mode, analyzer) for mode in MODES]
                for version, analyzer in analyzers.items()
            },
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(args.output)


if __name__ == "__main__":
    main()
