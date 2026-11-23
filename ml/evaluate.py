# ml/evaluate.py — Run locked Vietnamese evaluation and merge upstream English results.
import json
import os
from argparse import ArgumentParser
from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from subprocess import list2cmdline
from tempfile import TemporaryDirectory
from typing import Any

from apps.api.adapters import rules
from apps.api.schemas import AnalyzeRequest, Engine, Mode
from apps.api.services import analysis
from ml.bio import GOLD_LABELS, Span
from ml.dataset import MANIFEST_FILENAME, Note
from ml.evaluation_data import load_heldout, read_object
from ml.generate_data import DEFAULT_DATA_DIR
from ml.model import DEFAULT_MODEL_DIR, METADATA_FILENAME
from ml.scoring import Metrics, score_documents

OUTPUT_DIR = DEFAULT_MODEL_DIR.parent
VI_FILENAME = "evaluation-vi.json"
MERGED_FILENAME = "evaluation.json"
MODES: tuple[Mode, ...] = ("rules", "ner", "hybrid")
REPRODUCE_COMMAND = "python -m ml.evaluate"
RESULT_KEYS = {
    "language",
    "method",
    "status",
    "unit",
    "notes",
    "gold_entities",
    "micro",
    "by_label",
    "notes_with_fn",
    "examples",
}
EXAMPLE_KEYS = {"note_id", "kind", "label", "text", "start", "end"}


def _source_hash(path: str | None) -> str:
    """Hash runtime source with canonical line endings for reproducibility."""
    if path is None:
        raise ValueError("Evaluation engine source is unavailable.")
    return sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _unavailable_metrics(support: int) -> dict[str, int | None]:
    """Report known gold support with nulls for unobserved predictions and scores."""
    return dict.fromkeys(Metrics.__annotations__, None) | {"support": support}


def evaluate_mode(notes: Sequence[Note], mode: Mode) -> dict[str, Any]:
    """Run the real service for one mode and score it only if every note ran."""
    identity = {"language": "vi", "method": mode, "unit": "exact_span_label"}
    predictions: dict[str, list[Span]] = {}
    engine: Engine | None = None
    try:
        for note in notes:
            response = analysis.analyze_text(
                AnalyzeRequest(text=note.text, mode=mode, language="vi")
            )
            if engine is not None and response.engine != engine:
                raise ValueError(f"Engine identity changed during evaluation of {mode}.")
            engine = response.engine
            if engine.status != "available" or (engine.language, engine.mode) != ("vi", mode):
                raise ValueError(f"Unexpected engine identity during evaluation of {mode}.")
            predictions[note.note_id] = [
                Span(entity.start, entity.end, entity.label) for entity in response.entities
            ]
    except analysis.EngineUnavailableError:
        support = Counter(span.label for note in notes for span in note.entities)
        total = support.total()
        return {
            **identity,
            "status": "unavailable",
            "reason": "Engine yêu cầu chưa sẵn sàng cho toàn bộ tập test.",
            "command": REPRODUCE_COMMAND,
            "notes": len(notes),
            "gold_entities": total,
            "micro": _unavailable_metrics(total),
            "by_label": {label: _unavailable_metrics(support[label]) for label in GOLD_LABELS},
            "notes_with_fn": None,
            "examples": [],
        }
    if engine is None:
        raise ValueError("Cannot evaluate an empty corpus.")
    return {
        **identity,
        "status": "available",
        "engine": engine.model_dump(exclude_none=True),
        **score_documents(notes, predictions),
    }


def _model_metadata(results: Sequence[dict[str, Any]]) -> dict[str, Any] | None:
    """Read training config for the exact CRF revision used by successful modes."""
    revisions = {
        result["engine"]["model_revision"]
        for result in results
        if result["status"] == "available" and result["method"] != "rules"
    }
    if not revisions:
        return None
    model_dir = Path(os.environ.get("MEDSHIELD_MODEL_DIR") or DEFAULT_MODEL_DIR)
    metadata = read_object(model_dir / METADATA_FILENAME)
    if revisions != {metadata.get("revision")}:
        raise ValueError("CRF revision differs from evaluation engine metadata.")
    return metadata


def evaluate_vietnamese() -> dict[str, Any]:
    """Evaluate the three Vietnamese modes on the same frozen synthetic test corpus."""
    notes, test = load_heldout(DEFAULT_DATA_DIR)
    development = read_object(DEFAULT_DATA_DIR / MANIFEST_FILENAME)
    results = [evaluate_mode(notes, mode) for mode in MODES]
    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "datasets": {
            "vi": {
                "source": test["provenance"],
                "train_notes": development["splits"]["train"]["notes"],
                "validation_notes": development["splits"]["validation"]["notes"],
                "test_notes": len(notes),
                "participant_reviewed_count": test["participant_reviewed_count"],
            },
        },
        "metadata": {
            "vi": {
                "test_manifest": test,
                "development_manifest": development,
                "model": _model_metadata(results),
                "rules_source_sha256": _source_hash(rules.__file__),
                "analysis_source_sha256": _source_hash(analysis.__file__),
                "reproduce": REPRODUCE_COMMAND,
                "f1_target": 0.85,
            }
        },
        "results": results,
    }


def _english_results(english: dict[str, Any]) -> list[dict[str, Any]]:
    """Check the shared row schema and English-only identity before merging."""
    rows = english.get("results")
    if not isinstance(rows, list) or not rows:
        raise ValueError("English evaluation artifact must have a nonempty results array.")
    seen: set[tuple[str, str]] = set()
    for row in rows:
        if (
            not isinstance(row, dict)
            or not RESULT_KEYS <= row.keys()
            or row["language"] != "en"
            or not isinstance(row["method"], str)
            or not row["method"]
            or row["status"] not in ("available", "unavailable")
            or row["unit"] not in ("exact_span_label", "redaction_region")
            or not isinstance(row["examples"], list)
            or any(
                not isinstance(example, dict) or not EXAMPLE_KEYS <= example.keys()
                for example in row["examples"]
            )
        ):
            raise ValueError("Invalid English evaluation result row.")
        metrics = row["micro"]
        by_label = row["by_label"]
        unavailable = row["status"] == "unavailable"
        if (
            not isinstance(by_label, dict)
            or not (unavailable and metrics is None or _metric_fields_present(metrics))
            or not all(_metric_fields_present(stats) for stats in by_label.values())
        ):
            raise ValueError("Invalid English evaluation metric fields.")
        key = (row["method"], row["unit"])
        if key in seen:
            raise ValueError("Duplicate English evaluation method and unit.")
        seen.add(key)
    return rows


def _metric_fields_present(stats: object) -> bool:
    """Check required metric keys while preserving the English producer's values."""
    return isinstance(stats, dict) and Metrics.__required_keys__ <= stats.keys()


def _english_dataset(english: dict[str, Any], rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Expose English dataset summary for the UI, preferring the producer's summary."""
    datasets = english.get("datasets")
    if isinstance(datasets, dict) and isinstance(datasets.get("en"), dict):
        return dict(datasets["en"])
    dataset = english.get("dataset")
    if not isinstance(dataset, dict):
        dataset = {}
    return {
        "source": dataset.get("source")
        or dataset.get("provenance")
        or "Ghi chú giả lập tiếng Anh.",
        "test_notes": dataset.get(
            "test_notes", dataset.get("note_count", dataset.get("notes", rows[0]["notes"]))
        ),
        "participant_reviewed_count": dataset.get(
            "participant_reviewed_count", dataset.get("human_reviewed_notes")
        ),
    }


def merge_english(
    vietnamese: dict[str, Any], english: dict[str, Any], command: str
) -> dict[str, Any]:
    """Append English rows without altering their results or dropping producer metadata."""
    rows = _english_results(english)
    return {
        **vietnamese,
        "datasets": {**vietnamese["datasets"], "en": _english_dataset(english, rows)},
        "metadata": {
            **vietnamese["metadata"],
            "en": {key: value for key, value in english.items() if key != "results"},
            "merge_command": command,
        },
        "results": [*vietnamese["results"], *rows],
    }


def _write_artifact(path: Path, artifact: dict[str, Any]) -> None:
    """Publish a complete UTF-8 artifact by replacing it from the same directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(artifact, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    with TemporaryDirectory(dir=path.parent) as directory:
        staged = Path(directory) / path.name
        staged.write_bytes(payload.encode("utf-8"))
        staged.replace(path)


def main() -> None:
    """Write Vietnamese results and optionally publish the merged evaluation artifact."""
    parser = ArgumentParser(description="Chấm tập test tiếng Việt và ghép đối chứng tiếng Anh.")
    parser.add_argument("--english", type=Path, help="Artifact tiếng Anh do DevOps tạo.")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    vi_path = args.output_dir / VI_FILENAME
    if args.english and args.english.resolve() in {
        vi_path.resolve(),
        (args.output_dir / MERGED_FILENAME).resolve(),
    }:
        parser.error("Tệp tiếng Anh phải khác các tệp đầu ra.")
    vietnamese = evaluate_vietnamese()
    _write_artifact(vi_path, vietnamese)
    written = [vi_path]
    if args.english:
        parts = ["python", "-m", "ml.evaluate", "--english", str(args.english)]
        if args.output_dir != OUTPUT_DIR:
            parts.extend(["--output-dir", str(args.output_dir)])
        reused = merge_english(vietnamese, read_object(args.english), list2cmdline(parts))
        merged_path = args.output_dir / MERGED_FILENAME
        _write_artifact(merged_path, reused)
        written.append(merged_path)
    print(json.dumps({"artifacts": [str(path) for path in written]}))


if __name__ == "__main__":
    main()
