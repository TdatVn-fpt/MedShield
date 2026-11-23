# apps/api/adapters/ner.py — Load the project CRF and normalize model spans for the API.
import os
from functools import lru_cache
from pathlib import Path

from apps.api.schemas import Entity
from ml.model import DEFAULT_MODEL_DIR, METADATA_FILENAME, WEIGHTS_FILENAME, CrfModel, load_model

SOURCE = "medshield-crf"


@lru_cache(maxsize=2)
def _load(directory: Path, _artifact_stamps: tuple[int, int]) -> CrfModel:
    """_load validates and caches a model until either artifact changes."""
    return load_model(directory)


def available_model() -> CrfModel | None:
    """available_model reads actual model readiness without caching failed loads."""
    configured = os.environ.get("MEDSHIELD_MODEL_DIR")
    try:
        directory = Path(configured).resolve() if configured else DEFAULT_MODEL_DIR
        metadata_stamp = (directory / METADATA_FILENAME).stat().st_mtime_ns
        weights_stamp = (directory / WEIGHTS_FILENAME).stat().st_mtime_ns
        return _load(directory, (metadata_stamp, weights_stamp))
    except (OSError, ValueError, RuntimeError):
        return None


def recognize(text: str, model: CrfModel) -> list[Entity]:
    """recognize returns source-tagged code-point spans directly on the original text."""
    return [
        Entity(
            start=item.start,
            end=item.end,
            label=item.label,
            score=item.score,
            source=SOURCE,
        )
        for item in model.predict(text)
    ]
