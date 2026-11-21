# apps/api/main.py — Configure the local API with safe errors and no input persistence.
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse, Response

from apps.api.controllers import router
from apps.api.schemas import MAX_ENTITIES
from apps.api.services.analysis import AnalysisEntityLimitError, EngineUnavailableError
from apps.api.services.redaction import InvalidSpanError

app = FastAPI(title="MedShield", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


def error_response(status: int, code: str, message: str) -> JSONResponse:
    """error_response returns a minimal envelope without validation input or exception text."""
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


@app.exception_handler(HTTPException)
@app.exception_handler(RequestValidationError)
async def validation_error(
    request: Request, exception: RequestValidationError | HTTPException
) -> Response:
    """validation_error hides invalid body details and preserves unrelated HTTP errors."""
    if isinstance(exception, HTTPException) and not (
        exception.status_code == 400 and isinstance(exception.__cause__, UnicodeDecodeError)
    ):
        return await http_exception_handler(request, exception)
    return error_response(422, "VALIDATION_ERROR", "Dữ liệu yêu cầu không hợp lệ.")


@app.exception_handler(AnalysisEntityLimitError)
async def analysis_entity_limit(
    _request: Request, _exception: AnalysisEntityLimitError
) -> JSONResponse:
    """analysis_entity_limit returns a safe validation error with no partial detections."""
    return error_response(
        422,
        "VALIDATION_ERROR",
        f"Phát hiện quá {MAX_ENTITIES} vùng cần che. Hãy chia văn bản thành các phần nhỏ hơn.",
    )


@app.exception_handler(InvalidSpanError)
async def span_error(_request: Request, _exception: InvalidSpanError) -> JSONResponse:
    """span_error explains invalid or overlapping selections without repeating source text."""
    return error_response(422, "INVALID_SPAN", "Vị trí đoạn không hợp lệ hoặc chồng lấn.")


@app.exception_handler(EngineUnavailableError)
async def engine_error(_request: Request, _exception: EngineUnavailableError) -> JSONResponse:
    """engine_error exposes actual unavailable status without falling back to another mode."""
    return error_response(503, "ENGINE_UNAVAILABLE", "Engine được chọn hiện chưa khả dụng.")


@app.middleware("http")
async def private_response(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """private_response prevents caching and keeps unexpected exceptions out of server logs.

    Catching errors inside middleware avoids ServerErrorMiddleware re-raising an
    engine exception whose message could otherwise contain the original input.
    """
    try:
        response = await call_next(request)
    except Exception:
        response = error_response(500, "INTERNAL_ERROR", "Không thể xử lý yêu cầu lúc này.")
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


app.include_router(router)
