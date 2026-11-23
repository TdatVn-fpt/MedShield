# tests/test_privacy.py — Exercise safe failures and request limits at the HTTP boundary.
import pytest
from fastapi.testclient import TestClient

from apps.api import controllers
from apps.api.main import app

CANARY = "QA_SECRET_ERROR_CANARY_1b9"


def test_engine_exception_does_not_leak_request_or_exception(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Unexpected engine errors must return a generic500 without leaking body or exception."""

    def crash(*_args: object, **_kwargs: object) -> None:
        """crash injects a sensitive exception to verify the outer privacy boundary."""
        raise RuntimeError(CANARY)

    monkeypatch.setattr(controllers, "analyze_text", crash)
    response = TestClient(app, raise_server_exceptions=False).post(
        "/api/analyze", json={"text": CANARY, "language": "vi", "mode": "rules"}
    )
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert response.headers["cache-control"] == "no-store"
    assert CANARY not in response.text
    assert CANARY not in caplog.text


def test_unknown_request_fields_and_too_many_spans_are_rejected() -> None:
    """Extra request fields and more than2000 spans must fail before business processing."""
    client = TestClient(app)
    extra = client.post(
        "/api/analyze",
        json={"text": CANARY, "language": "vi", "mode": "rules", "patient": CANARY},
    )
    entity = {"start": 0, "end": 1, "label": "NAME", "source": "manual", "score": 1}
    oversized = client.post("/api/redact", json={"text": CANARY, "entities": [entity] * 2001})
    for response in [extra, oversized]:
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"
        assert CANARY not in response.text
