# tests/test_api_contract.py — Independent QA checks for the public HTTP contract.
import json
import unicodedata

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)
CANARY = "QA_PRIVATE_CANARY_7c2f"


def span(text: str, value: str, label: str, offset: int = 0) -> dict[str, object]:
    """span locates a synthetic value and returns a manual codepoint entity."""
    start = text.index(value, offset)
    return {
        "start": start,
        "end": start + len(value),
        "label": label,
        "source": "manual",
        "score": 1,
    }


def test_analyze_new_sentence_keeps_followup_date() -> None:
    """A new QA sentence must use real rules and preserve its follow-up date."""
    text = "Người bệnh Đỗ Minh Lâm, sinh ngày 12/04/1988, mã BN-90412. Hẹn khám lại 23/12."
    response = client.post("/api/analyze", json={"text": text, "language": "vi", "mode": "rules"})
    assert response.status_code == 200
    result = response.json()
    assert result["engine"]["mode"] == "rules"
    assert result["engine"]["status"] == "available"
    predicted = {(text[e["start"] : e["end"]], e["label"]) for e in result["entities"]}
    assert ("Đỗ Minh Lâm", "NAME") in predicted
    assert ("12/04/1988", "DOB") in predicted
    assert ("BN-90412", "ID") in predicted
    assert "23/12" in result["redacted_text"]
    assert "Đỗ Minh Lâm" not in result["redacted_text"]


def test_redact_respects_edits_repeated_names_and_metadata() -> None:
    """Redact must use only submitted spans, reuse exact names and reset per document."""
    text = "🙂 Mai An gọi Mai An. Hẹn 18/12. Mã HS-819."
    first = span(text, "Mai An", "NAME")
    second = span(text, "Mai An", "NAME", text.index("Mai An") + len("Mai An"))
    response = client.post("/api/redact", json={"text": text, "entities": [second, first]})
    assert response.status_code == 200
    result = response.json()
    assert set(result) == {"redacted_text", "metadata"}
    assert result["redacted_text"] == "🙂 [NAME_1] gọi [NAME_1]. Hẹn 18/12. Mã HS-819."
    assert result["metadata"]["entity_count"] == 2
    assert result["metadata"]["counts_by_label"]["NAME"] == 2
    assert result["metadata"]["offset_unit"] == "unicode_code_point"
    reset = client.post(
        "/api/redact", json={"text": "Mai An", "entities": [span("Mai An", "Mai An", "NAME")]}
    )
    assert reset.json()["redacted_text"] == "[NAME_1]"
    removed = client.post("/api/redact", json={"text": text, "entities": []})
    assert removed.json()["redacted_text"] == text
    relabeled = client.post(
        "/api/redact", json={"text": text, "entities": [{**first, "label": "ADDR"}]}
    )
    assert relabeled.json()["redacted_text"].startswith("🙂 [ADDR_1] gọi Mai An")


def test_redact_unicode_combining_crlf_preserves_original() -> None:
    """Codepoint offsets must preserve NFD text, an emoji and Windows line endings."""
    name = unicodedata.normalize("NFD", "Nguyễn Ánh")
    text = f"🙂\r\nNgười bệnh {name}.\r\nTái khám 04/12."
    response = client.post(
        "/api/redact", json={"text": text, "entities": [span(text, name, "NAME")]}
    )
    assert response.status_code == 200
    assert response.json()["redacted_text"] == "🙂\r\nNgười bệnh [NAME_1].\r\nTái khám 04/12."


@pytest.mark.parametrize(
    "entities",
    [
        [{"start": -1, "end": 2, "label": "NAME", "source": "manual", "score": 1}],
        [{"start": 1, "end": 1, "label": "NAME", "source": "manual", "score": 1}],
        [{"start": 0, "end": 1000, "label": "NAME", "source": "manual", "score": 1}],
        [
            {"start": 0, "end": 5, "label": "NAME", "source": "manual", "score": 1},
            {"start": 4, "end": 8, "label": "ADDR", "source": "manual", "score": 1},
        ],
    ],
)
def test_invalid_span_errors_are_safe(entities: list[dict[str, object]]) -> None:
    """Invalid ranges and conflicts must fail without returning any submitted text."""
    response = client.post("/api/redact", json={"text": CANARY, "entities": entities})
    assert response.status_code == 422
    assert set(response.json()) == {"error"}
    assert CANARY not in response.text
    assert "input" not in response.json()["error"]


@pytest.mark.parametrize(
    "change",
    [
        {"start": True},
        {"start": 1.5},
        {"label": "EMAIL"},
        {"score": -0.1},
        {"score": 1.1},
        {"extra": CANARY},
    ],
)
def test_invalid_entity_fields_are_safe(change: dict[str, object]) -> None:
    """Strict entity validation must reject coercion, unknown labels and extra fields."""
    entity = {"start": 0, "end": 2, "label": "NAME", "source": "manual", "score": 1, **change}
    response = client.post("/api/redact", json={"text": CANARY, "entities": [entity]})
    assert response.status_code == 422
    assert set(response.json()) == {"error"}
    assert CANARY not in response.text


@pytest.mark.parametrize("text", ["", " \r\n\t", "a" * 50001])
def test_invalid_text_is_rejected(text: str) -> None:
    """Empty, whitespace-only and oversized text must be rejected consistently."""
    response = client.post("/api/analyze", json={"text": text, "language": "vi", "mode": "rules"})
    assert response.status_code == 422
    assert set(response.json()) == {"error"}


def test_malformed_json_and_missing_fields_do_not_leak(caplog: pytest.LogCaptureFixture) -> None:
    """JSON and schema errors must use safe envelopes and avoid input-bearing logs."""
    malformed = client.post(
        "/api/analyze", content='{"text":"' + CANARY, headers={"content-type": "application/json"}
    )
    missing = client.post("/api/analyze", json={"text": CANARY})
    for response in [malformed, missing]:
        assert response.status_code == 422
        assert set(response.json()) == {"error"}
        assert CANARY not in response.text
    assert CANARY not in caplog.text


def test_adjacent_spans_are_allowed_and_duplicates_rejected() -> None:
    """Touching ranges are distinct; identical ranges conflict even with same label."""
    entities = [span("MaiAn", "Mai", "NAME"), span("MaiAn", "An", "NAME")]
    adjacent = client.post("/api/redact", json={"text": "MaiAn", "entities": entities})
    assert adjacent.status_code == 200
    assert adjacent.json()["redacted_text"] == "[NAME_1][NAME_2]"
    duplicate = client.post(
        "/api/redact", json={"text": "MaiAn", "entities": [entities[0], entities[0]]}
    )
    assert duplicate.status_code == 422


def test_unavailable_mode_is_not_silently_replaced() -> None:
    """An unavailable advertised mode must return503, or identify its real available mode."""
    response = client.post(
        "/api/analyze", json={"text": "Người bệnh Mai An.", "language": "vi", "mode": "ner"}
    )
    if response.status_code == 503:
        assert response.json()["error"]["code"] == "ENGINE_UNAVAILABLE"
    else:
        assert response.status_code == 200
        assert response.json()["engine"]["mode"] == "ner"


def test_evaluation_has_explicit_availability() -> None:
    """Evaluation must distinguish a real artifact from an unavailable result."""
    response = client.get("/api/evaluation")
    assert response.status_code == 200
    result = response.json()
    assert result["status"] in {"available", "unavailable"}
    if result["status"] == "unavailable":
        assert "reason" in result
        assert "evaluation" not in result
    assert CANARY not in json.dumps(result)
