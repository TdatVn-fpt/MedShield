# tests/test_g1_regressions.py — Cover G1 engine availability and safe analysis boundaries.
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def test_health_matches_analysis_when_model_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Health and requests both expose real availability with no model installed."""
    monkeypatch.setenv("MEDSHIELD_MODEL_DIR", str(tmp_path))
    notes = {"vi": "Người bệnh Mai An.", "en": "Patient Mai An."}
    expected = {
        (language, mode): "available" if mode == "rules" else "unavailable"
        for language in notes
        for mode in ("rules", "ner", "hybrid")
    }
    health = client.get("/health")
    assert health.status_code == 200
    result = health.json()
    assert result["status"] == "ok"
    rows = result["engines"]
    assert len(rows) == len(expected)
    assert {(row["language"], row["mode"]): row["status"] for row in rows} == expected

    for row in rows:
        language = row["language"]
        response = client.post(
            "/api/analyze",
            json={"text": notes[language], "language": language, "mode": row["mode"]},
        )
        if row["status"] == "available":
            assert response.status_code == 200
            analysis = response.json()
            assert analysis["engine"] == row
            assert "[NAME_1]" in analysis["redacted_text"]
            assert "Mai An" not in analysis["redacted_text"]
        else:
            assert response.status_code == 503
            assert response.json()["error"]["code"] == "ENGINE_UNAVAILABLE"


def test_analysis_rejects_more_than_2000_spans_without_partial_output() -> None:
    """The first count above the review limit fails without returning text or spans."""
    phone = "0912345678"
    note = " ".join([phone] * 2_001)
    response = client.post("/api/analyze", json={"text": note, "language": "vi", "mode": "rules"})
    assert response.status_code == 422
    assert response.headers["cache-control"] == "no-store"
    result = response.json()
    assert set(result) == {"error"}
    assert set(result["error"]) == {"code", "message"}
    assert result["error"]["code"] == "VALIDATION_ERROR"
    assert phone not in response.text


def test_analysis_at_2000_spans_can_be_redacted() -> None:
    """The maximum valid analysis returns the complete list and a usable preview."""
    note = " ".join(["0912345678"] * 2_000)
    response = client.post("/api/analyze", json={"text": note, "language": "vi", "mode": "rules"})
    assert response.status_code == 200
    result = response.json()
    assert len(result["entities"]) == 2_000
    redaction = client.post("/api/redact", json={"text": note, "entities": result["entities"]})
    assert redaction.status_code == 200
    assert redaction.json()["redacted_text"] == result["redacted_text"]
    assert redaction.json()["metadata"]["entity_count"] == 2_000


def test_blank_name_candidate_does_not_block_later_detections() -> None:
    """Ignoring a whitespace-only candidate preserves the rest of the original note."""
    note = "Patient    , observation. Patient Mai An."
    response = client.post("/api/analyze", json={"text": note, "language": "en", "mode": "rules"})
    assert response.status_code == 200
    result = response.json()
    spans = [
        (note[entity["start"] : entity["end"]], entity["label"]) for entity in result["entities"]
    ]
    assert spans == [("Mai An", "NAME")]
    assert result["redacted_text"] == "Patient    , observation. Patient [NAME_1]."


@pytest.mark.parametrize("endpoint", ["/api/analyze", "/api/redact"])
def test_invalid_utf8_json_returns_safe_validation_error(
    endpoint: str, caplog: pytest.LogCaptureFixture
) -> None:
    """An undecodable JSON body returns the shared envelope without logging or echoing bytes."""
    canary = "G1_PRIVATE_CANARY_46ab"
    response = client.post(
        endpoint,
        content=b'{"text":"' + canary.encode() + b'\xff"}',
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert response.headers["cache-control"] == "no-store"
    result = response.json()
    assert set(result) == {"error"}
    assert set(result["error"]) == {"code", "message"}
    assert result["error"]["code"] == "VALIDATION_ERROR"
    assert canary not in response.text
    assert canary not in caplog.text


@pytest.mark.parametrize("encoding", ["utf-16-le", "utf-16", "utf-32-le", "utf-32"])
def test_json_encoding_is_not_auto_detected(encoding: str) -> None:
    """Both routes reject non-UTF-8 encodings even when the JSON object is valid."""
    requests = {
        "/api/analyze": '{"text":"QA fixture.","language":"en","mode":"rules"}',
        "/api/redact": '{"text":"QA fixture.","entities":[]}',
    }
    for endpoint, payload in requests.items():
        response = client.post(
            endpoint,
            content=payload.encode(encoding),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"
