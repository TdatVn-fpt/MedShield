# apps/api/services/analysis.py — Select real engines and construct machine-analysis responses.
from apps.api.adapters.rules import recognize
from apps.api.schemas import MAX_ENTITIES, AnalyzeRequest, AnalyzeResponse, Engine, Language, Mode
from apps.api.services.redaction import redact_text


class EngineUnavailableError(Exception):
    """EngineUnavailableError means the requested configuration did not run."""


class AnalysisEntityLimitError(Exception):
    """AnalysisEntityLimitError rejects a result too large to review as a complete list."""


def engine_info(mode: Mode, language: Language) -> Engine:
    """engine_info reports actual G1 rules readiness; model configurations remain unavailable."""
    return Engine(
        name=f"medshield-{mode}",
        mode=mode,
        language=language,
        status="available" if mode == "rules" else "unavailable",
        version="0.1.0",
    )


def analyze_text(request: AnalyzeRequest) -> AnalyzeResponse:
    """analyze_text returns complete detections and a preview or raises on unavailable/limit."""
    engine = engine_info(request.mode, request.language)
    if engine.status != "available":
        raise EngineUnavailableError
    entities = recognize(request.text)
    if len(entities) > MAX_ENTITIES:
        raise AnalysisEntityLimitError
    preview = redact_text(request.text, entities)
    return AnalyzeResponse(
        entities=entities,
        redacted_text=preview.redacted_text,
        engine=engine,
    )
