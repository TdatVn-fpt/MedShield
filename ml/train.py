# ml/train.py — Fit a CPU CRF, select it on validation and export native model artifacts.
import json
import platform
from argparse import ArgumentParser
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from fractions import Fraction
from importlib.metadata import version
from pathlib import Path
from tempfile import TemporaryDirectory

import sklearn_crfsuite

from ml.bio import MODEL_LABELS, Span, encode_bio
from ml.dataset import Dataset, Note, load_dataset
from ml.features import Feature, extract_features
from ml.generate_data import DEFAULT_DATA_DIR
from ml.model import (
    DEFAULT_MODEL_DIR,
    METADATA_FILENAME,
    WEIGHTS_FILENAME,
    CrfModel,
    model_identity,
)
from ml.tokenization import tokenize


@dataclass(frozen=True, slots=True)
class TrainingConfig:
    """TrainingConfig holds deterministic CPU CRFsuite optimizer options."""

    c1: float
    c2: float
    max_iterations: int = 100
    algorithm: str = "lbfgs"
    all_possible_transitions: bool = True


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """ValidationResult records exact-span counts for the supported CRF labels."""

    tp: int
    fp: int
    fn: int

    @property
    def f1(self) -> Fraction:
        """Return exact micro-F1 for stable candidate comparisons and ties."""
        denominator = 2 * self.tp + self.fp + self.fn
        return Fraction(2 * self.tp, denominator) if denominator else Fraction(0)


DEFAULT_CONFIGS = (TrainingConfig(0.05, 0.1), TrainingConfig(0.1, 0.1), TrainingConfig(0.1, 0.5))


def _validate(model: CrfModel, notes: Sequence[Note]) -> ValidationResult:
    """Count exact (start, end, label) matches per note before any manual edits."""
    tp = fp = fn = 0
    for note in notes:
        gold = {span for span in note.entities if span.label in MODEL_LABELS}
        predicted = {Span(p.start, p.end, p.label) for p in model.predict(note.text)}
        tp += len(gold & predicted)
        fp += len(predicted - gold)
        fn += len(gold - predicted)
    return ValidationResult(tp, fp, fn)


def _training_sequences(
    notes: Sequence[Note],
) -> tuple[list[list[dict[str, Feature]]], list[list[str]]]:
    """Build shared feature and BIO sequences, with informative gold alignment errors."""
    features: list[list[dict[str, Feature]]] = []
    tags: list[list[str]] = []
    for note in notes:
        tokens = tokenize(note.text)
        features.append(extract_features(note.text, tokens))
        try:
            tags.append(encode_bio(tokens, note.entities))
        except ValueError as error:
            raise ValueError(f"Token alignment failed for note {note.note_id}.") from error
    return features, tags


def train(
    dataset: Dataset, configs: Sequence[TrainingConfig], output_dir: Path
) -> dict[str, object]:
    """Fit on train, pick highest validation micro-F1 and publish native model and metadata."""
    if not configs:
        raise ValueError("At least one training configuration is required.")
    features, tags = _training_sequences(dataset.train)
    _training_sequences(dataset.validation)
    results: list[dict[str, object]] = []
    best_f1 = Fraction(-1)
    selected = 0
    best_weights = b""
    output_dir.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output_dir) as workspace:
        staging = Path(workspace)
        for index, config in enumerate(configs):
            candidate_path = staging / f"candidate-{index}.crfsuite"
            estimator = sklearn_crfsuite.CRF(model_filename=str(candidate_path), **asdict(config))
            estimator.fit(features, tags)
            weights = candidate_path.read_bytes()
            result = _validate(CrfModel(weights), dataset.validation)
            results.append(
                {"config": asdict(config), **asdict(result), "micro_f1": float(result.f1)}
            )
            if result.f1 > best_f1:
                best_f1, selected, best_weights = result.f1, index, weights

        metadata: dict[str, object] = {
            **model_identity(best_weights),
            "language": "vi",
            "device": "cpu",
            "runtime": {
                "python": platform.python_version(),
                "sklearn_crfsuite": version("sklearn-crfsuite"),
                "python_crfsuite": version("python-crfsuite"),
                "scikit_learn": version("scikit-learn"),
            },
            "dataset": {
                "revision": dataset.revision,
                "generator_seed": dataset.seed,
                "manifest_sha256": dataset.manifest_sha256,
                "split_sha256": dataset.split_sha256,
                "train_notes": len(dataset.train),
                "validation_notes": len(dataset.validation),
            },
            "training_config": asdict(configs[selected]),
            "selection": {
                "split": "validation",
                "metric": "exact_span_label_micro_f1",
                "tie_break": "first_candidate",
                "selected_index": selected,
                "candidates": results,
            },
            "reproduce": [
                f"python -m ml.generate_data --seed {dataset.seed}",
                "python -m ml.train",
            ],
        }
        staged_weights = staging / WEIGHTS_FILENAME
        staged_metadata = staging / METADATA_FILENAME
        staged_weights.write_bytes(best_weights)
        staged_metadata.write_bytes((json.dumps(metadata, indent=2) + "\n").encode("utf-8"))
        staged_weights.replace(output_dir / WEIGHTS_FILENAME)
        staged_metadata.replace(output_dir / METADATA_FILENAME)
    return metadata


def main() -> None:
    """Train using the two manifest splits and write the chosen native CRFsuite model."""
    parser = ArgumentParser(description="Huấn luyện NER tiếng Việt bằng CRF trên CPU.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_MODEL_DIR)
    args = parser.parse_args()
    metadata = train(load_dataset(args.data_dir), DEFAULT_CONFIGS, args.output_dir)
    print(json.dumps({"revision": metadata["revision"], "model_dir": str(args.output_dir)}))


if __name__ == "__main__":
    main()
