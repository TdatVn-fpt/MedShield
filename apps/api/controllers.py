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
            or not all(_valid_evaluation_result(result) for result in results)
        ):
            raise ValueError("invalid artifact")
    except (OSError, ValueError):
        return {"status": "unavailable", "reason": "Chưa có kết quả đánh giá."}
    return {"status": "available", "evaluation": artifact}


def _valid_metrics(value: object) -> bool:
    """_valid_metrics checks displayable counts and fractional metrics from an artifact."""
    if not isinstance(value, dict):
        return False
    for key in ("tp", "fp", "fn", "support"):
        count = value.get(key)
        if type(count) is not int or count < 0:
            return False
    for key in ("precision", "recall", "f1"):
        fraction = value.get(key)
        if not isinstance(fraction, int | float) or isinstance(fraction, bool):
            return False
        if not 0 <= fraction <= 1:
            return False
    return True


def _valid_evaluation_result(value: object) -> bool:
    """_valid_evaluation_result rejects rows the dashboard cannot display reliably."""
    if (
        not isinstance(value, dict)
        or value.get("language") not in ("vi", "en")
        or not isinstance(value.get("method"), str)
    ):
        return False
    if value.get("status") == "unavailable":
        return isinstance(value.get("reason"), str)
    if value.get("status") != "available" or not _valid_metrics(value.get("micro")):
        return False
    labels = value.get("by_label")
    examples = value.get("examples")
    return (
        isinstance(labels, dict)
        and all(_valid_metrics(item) for item in labels.values())
        and isinstance(examples, list)
        and all(
            isinstance(item, dict)
            and item.get("kind") in ("FP", "FN")
            and isinstance(item.get("note_id"), str)
            and isinstance(item.get("text"), str)
            for item in examples
        )
    )
