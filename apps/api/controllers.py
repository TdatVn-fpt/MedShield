# apps/api/controllers.py — Route HTTP requests through validated services and artifact reads.
import json
from pathlib import Path
from typing import Any, get_args

from fastapi import APIRouter

from apps.api.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    Language,
    Mode,
    RedactRequest,
    RedactResponse,
)
from apps.api.services.analysis import analyze_text, engine_info
from apps.api.services.redaction import redact_text

router = APIRouter()
EVALUATION_PATH = Path(__file__).resolve().parents[2] / "artifacts" / "evaluation.json"


@router.get("/health")
def health() -> dict[str, Any]:
    """health returns API liveness and availability for every accepted language/mode pair."""
    return {
        "status": "ok",
        "engines": [
            engine_info(mode, language).model_dump(exclude_none=True)
            for language in get_args(Language)
            for mode in get_args(Mode)
        ],
    }


@router.post("/api/analyze", response_model=AnalyzeResponse, response_model_exclude_none=True)
def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    """analyze validates the HTTP contract before delegating machine inference."""
    return analyze_text(request)


@router.post("/api/redact", response_model=RedactResponse)
def redact(request: RedactRequest) -> RedactResponse:
    """redact uses exactly the submitted reviewed spans, without re-detection."""
    return redact_text(request.text, request.entities)


@router.get("/api/evaluation")
def evaluation() -> dict[str, Any]:
    """evaluation reads a real script-produced artifact or explicitly reports its absence."""
    try:
        artifact = json.loads(EVALUATION_PATH.read_text(encoding="utf-8"))
        results = artifact.get("results") if isinstance(artifact, dict) else None
        if (
            not isinstance(results, list)
            or not results
            or not all(
                isinstance(result, dict)
                and result.get("language") in ("vi", "en")
                and isinstance(result.get("method"), str)
                and result.get("status") in ("available", "unavailable")
                for result in results
            )
        ):
            raise ValueError("invalid artifact")
    except (OSError, ValueError):
        return {"status": "unavailable", "reason": "Chưa có kết quả đánh giá."}
    return {"status": "available", "evaluation": artifact}
