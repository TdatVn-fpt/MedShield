# ml/model.py — Load verified native CRFsuite weights and predict exact source spans.
import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from threading import Lock

import pycrfsuite

from ml.bio import MODEL_LABELS, MODEL_TAGS, ModelLabel, decode_bio
from ml.features import FEATURES_VERSION, extract_features
from ml.tokenization import TOKENIZER_VERSION, tokenize

DEFAULT_MODEL_DIR = Path(__file__).resolve().parents[1] / "artifacts" / "model"
WEIGHTS_FILENAME = "model.crfsuite"
METADATA_FILENAME = "metadata.json"
MODEL_SCHEMA_VERSION = 1


class ModelLoadError(ValueError):
    """ModelLoadError indicates missing, incompatible or corrupt model artifacts."""


@dataclass(frozen=True, slots=True)
class Prediction:
    """Prediction carries source code point offsets, model label and uncalibrated score."""

    start: int
    end: int
    label: ModelLabel
    score: float


def model_identity(weights: bytes) -> dict[str, object]:
    """Return the compatibility metadata and content identity of native model bytes."""
    digest = sha256(weights).hexdigest()
    return {
        "schema_version": MODEL_SCHEMA_VERSION,
        "format": "crfsuite",
        "weights_file": WEIGHTS_FILENAME,
        "weights_sha256": digest,
        "revision": f"sha256:{digest}",
        "labels": list(MODEL_LABELS),
        "tokenizer_version": TOKENIZER_VERSION,
        "features_version": FEATURES_VERSION,
    }


class CrfModel:
    """CrfModel holds one verified native tagger snapshot for CPU inference."""

    def __init__(self, weights: bytes) -> None:
        """Open native weights in memory and validate their supported BIO vocabulary."""
        if not weights.startswith(b"lCRF"):
            raise ModelLoadError("Invalid CRFsuite file signature.")
        self._weights = weights
        self.revision = f"sha256:{sha256(weights).hexdigest()}"
        self._tagger = pycrfsuite.Tagger()
        self._lock = Lock()
        try:
            # The native model borrows this buffer for the lifetime of its tagger.
            self._tagger.open_inmemory(self._weights)
            if set(self._tagger.labels()) != MODEL_TAGS:
                raise ModelLoadError("CRF model has an incompatible BIO vocabulary.")
        except (RuntimeError, ValueError, OSError) as error:
            raise ModelLoadError("CRF weights could not be loaded.") from error

    def predict(self, text: str) -> list[Prediction]:
        """Predict non-overlapping spans with minimum token-tag marginal per span."""
        tokens = tokenize(text)
        if not tokens:
            return []
        features = extract_features(text, tokens)
        with self._lock:
            tags = self._tagger.tag(features)
            return [
                Prediction(
                    item.span.start,
                    item.span.end,
                    item.label,
                    min(
                        self._tagger.marginal(tags[index], index)
                        for index in range(item.first_token, item.end_token)
                    ),
                )
                for item in decode_bio(tokens, tags)
            ]


def load_model(model_dir: Path = DEFAULT_MODEL_DIR) -> CrfModel:
    """Load metadata and native weights; raise ModelLoadError on any artifact mismatch."""
    try:
        metadata = json.loads((model_dir / METADATA_FILENAME).read_text(encoding="utf-8"))
        weights = (model_dir / WEIGHTS_FILENAME).read_bytes()
        if not isinstance(metadata, dict) or any(
            metadata.get(key) != value for key, value in model_identity(weights).items()
        ):
            raise ModelLoadError("CRF metadata does not match the model or runtime.")
        return CrfModel(weights)
    except ModelLoadError:
        raise
    except (ValueError, OSError) as error:
        raise ModelLoadError("CRF artifacts could not be read.") from error
