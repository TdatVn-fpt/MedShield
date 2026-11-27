# apps/api/services/analysis.py — Select real engines and construct machine-analysis responses.
from apps.api.adapters import ner, rules
from apps.api.adapters.vi_boundaries import refine
from apps.api.adapters.vi_names_places import repeat_names
from apps.api.schemas import (
    MAX_ENTITIES,
    AnalyzeRequest,
    AnalyzeResponse,
    Engine,
    Language,
    Mode,
)
from apps.api.services import hybrid
from apps.api.services.redaction import redact_text


class EngineUnavailableError(Exception):
    """EngineUnavailableError means the requested configuration did not run."""


class AnalysisEntityLimitError(Exception):
    """AnalysisEntityLimitError rejects a result too large to review as a complete list."""


def engine_info(mode: Mode, language: Language) -> Engine:
    """engine_info describes availability after attempting to load the selected engine."""
    model = ner.available_model() if mode != "rules" and language == "vi" else None
    return _engine_info(mode, language, model.revision if model else None)


def _engine_info(mode: Mode, language: Language, revision: str | None) -> Engine:
    """_engine_info creates metadata for the exact model revision obtained by its caller."""
    return Engine(
        name=f"medshield-{mode}",
        mode=mode,
        language=language,
        status="available" if mode == "rules" or revision is not None else "unavailable",
        version="0.3.0" if language == "vi" and mode != "ner" else "0.1.0",
        model_revision=revision,
    )


def analyze_text(request: AnalyzeRequest) -> AnalyzeResponse:
    """analyze_text returns complete detections and a preview or raises on unavailable/limit."""
    model = None
    if request.mode == "rules":
        entities = rules.recognize(request.text, request.language)
    else:
        model = ner.available_model() if request.language == "vi" else None
        if model is None:
            raise EngineUnavailableError
        entities = ner.recognize(request.text, model)
        if request.mode == "hybrid":
            entities = hybrid.combine(
                rules.vietnamese_candidates(request.text), refine(request.text, entities)
            )
    if request.language == "vi" and request.mode in {"rules", "hybrid"}:
        repeated = list(repeat_names(request.text, entities))
        if repeated:
            entities = rules.resolve_overlaps(entities + repeated, priority=hybrid.priority)
    engine = _engine_info(request.mode, request.language, model.revision if model else None)
    if len(entities) > MAX_ENTITIES:
        raise AnalysisEntityLimitError
    preview = redact_text(request.text, entities)
    return AnalyzeResponse(
        entities=entities,
        redacted_text=preview.redacted_text,
        engine=engine,
    )
