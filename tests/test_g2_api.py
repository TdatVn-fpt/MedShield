# tests/test_g2_api.py — Independently verify the G2 engine and Unicode API contracts.
import os
import re
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from unicodedata import normalize

import pytest
from fastapi.testclient import TestClient

from apps.api.adapters import ner
from apps.api.main import app
from apps.api.schemas import Entity, Label

MODEL_DIR = Path(__file__).resolve().parents[1] / "artifacts" / "model"
MODES = ("rules", "ner", "hybrid")
LANGUAGES = ("vi", "en")


@pytest.mark.parametrize("artifact_state", ["missing", "corrupt"])
def test_unavailable_model_keeps_rules_and_returns_safe_errors(
    artifact_state: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Missing and malformed artifacts leave rules available and prevent NER fallback."""
    directory = tmp_path / "G2_MODEL_PATH_CANARY"
    directory.mkdir()
    if artifact_state == "corrupt":
        (directory / "metadata.json").write_text("{", encoding="utf-8")
        (directory / "model.crfsuite").write_bytes(b"invalid weights")
    monkeypatch.setenv("MEDSHIELD_MODEL_DIR", str(directory))
    text_canary = "G2_SYNTHETIC_INPUT_CANARY"
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        rows = health.json()["engines"]
        assert len(rows) == 6
        assert {(row["language"], row["mode"]): row["status"] for row in rows} == {
            (language, mode): "available" if mode == "rules" else "unavailable"
            for language in LANGUAGES
            for mode in MODES
        }
        assert directory.name not in health.text
        for language in LANGUAGES:
            for mode in MODES:
                response = client.post(
                    "/api/analyze", json={"text": text_canary, "language": language, "mode": mode}
                )
                if mode == "rules":
                    assert response.status_code == 200
                    assert response.json()["engine"]["mode"] == "rules"
                    continue
                assert response.status_code == 503
                assert response.headers["cache-control"] == "no-store"
                result = response.json()
                assert set(result) == {"error"}
                assert set(result["error"]) == {"code", "message"}
                assert result["error"]["code"] == "ENGINE_UNAVAILABLE"
                assert text_canary not in response.text
                assert directory.name not in response.text
    assert text_canary not in caplog.text
    assert directory.name not in caplog.text


def test_rules_offsets_and_repeated_tokens_preserve_original_text() -> None:
    """Rules and the review endpoint round-trip NFD, emoji, BOM and CRLF exactly."""
    name = normalize("NFD", "Nguyễn Ánh")
    text = (
        f"\ufeff🙂\r\nNgười bệnh {name}; mã BN-93012.\r\nNgười bệnh {name}.\r\nHẹn tái khám 17/12."
    )
    expected = (
        "\ufeff🙂\r\nNgười bệnh [NAME_1]; mã [ID_1].\r\n"
        "Người bệnh [NAME_1].\r\nHẹn tái khám 17/12."
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/analyze", json={"text": text, "language": "vi", "mode": "rules"}
        )
        assert response.status_code == 200
        data = response.json()
        entities = data["entities"]
        assert [(item["start"], item["end"], item["label"]) for item in entities] == [
            (15, 28, "NAME"),
            (33, 41, "ID"),
            (55, 68, "NAME"),
        ]
        assert data["redacted_text"] == expected
        response = client.post(
            "/api/redact", json={"text": text, "entities": list(reversed(entities))}
        )
        assert response.status_code == 200
        assert response.json() == {
            "redacted_text": expected,
            "metadata": {
                "entity_count": 3,
                "counts_by_label": {"NAME": 2, "DOB": 0, "PHONE": 0, "ID": 1, "ADDR": 0},
                "offset_unit": "unicode_code_point",
            },
        }


def test_hybrid_prioritizes_label_and_source_over_score(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Controlled CRF spans exercise each precedence tier through the real hybrid endpoint."""
    text = (
        "🙂 Người bệnh Mai An, sinh ngày 12/04/1988; "
        "điện thoại 0912345678; mã BN-93012; địa chỉ: 24 đường Mây."
    )

    def predict(original: str, _model: object) -> list[Entity]:
        """Supply competing CRF spans crafted to lose or win despite their scores."""
        assert original == text
        candidates: tuple[tuple[str, Label, float], ...] = (
            ("Mai An", "NAME", 0.1),
            ("ngày 12/04/1988", "ADDR", 0.99),
            ("thoại 0912345678", "ADDR", 0.99),
            ("mã BN-93012", "ADDR", 0.99),
        )
        return [
            Entity(
                start=text.index(value),
                end=text.index(value) + len(value),
                label=label,
                source="medshield-crf",
                score=score,
            )
            for value, label, score in candidates
        ]

    monkeypatch.setattr(ner, "available_model", lambda: SimpleNamespace(revision="test-overlap"))
    monkeypatch.setattr(ner, "recognize", predict)
    with TestClient(app) as client:
        response = client.post(
            "/api/analyze", json={"text": text, "language": "vi", "mode": "hybrid"}
        )
    assert response.status_code == 200
    entities = response.json()["entities"]
    assert [
        (text[item["start"] : item["end"]], item["label"], item["source"]) for item in entities
    ] == [
        ("Mai An", "NAME", "medshield-crf"),
        ("12/04/1988", "DOB", "medshield-rules"),
        ("0912345678", "PHONE", "medshield-rules"),
        ("BN-93012", "ID", "medshield-rules"),
        ("24 đường Mây", "ADDR", "medshield-rules"),
    ]


@pytest.fixture
def published_model_revision(monkeypatch: pytest.MonkeyPatch) -> str:
    """Use the configured published weights and derive their revision independently."""
    directory = Path(os.environ.get("MEDSHIELD_MODEL_DIR") or MODEL_DIR).resolve()
    weights_path = directory / "model.crfsuite"
    metadata_path = directory / "metadata.json"
    if not weights_path.exists() and not metadata_path.exists():
        pytest.skip("G2 published CRF metadata and weights are required for this smoke test.")
    assert weights_path.is_file() and metadata_path.is_file(), "Incomplete published CRF artifact"
    monkeypatch.setenv("MEDSHIELD_MODEL_DIR", str(directory))
    return "sha256:" + sha256(weights_path.read_bytes()).hexdigest()


def test_published_model_serves_known_positive(published_model_revision: str) -> None:
    """The Lead's illustrative note proves real CRF NAME/ADDR and rules DOB through HTTP."""
    name = normalize("NFD", "Hạ Minh")
    dob = "20/02/1985"
    address = "64 đường Vân,\r\nphường Sương, quận Gió"
    text = (
        f"🧭 Họ và tên: {name}.\r\nNgày sinh: {dob}.\r\n"
        f"Địa chỉ nhận giấy hẹn:\r\n{address}.\r\n"
        "Căn dặn đem theo kết quả xét nghiệm."
    )
    assert text.count("\r\n") == 5
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        rows = health.json()["engines"]
        assert len(rows) == 6
        engines = {(item["language"], item["mode"]): item for item in rows}
        assert set(engines) == {(language, mode) for language in LANGUAGES for mode in MODES}
        for mode in ("ner", "hybrid"):
            assert engines["en", mode]["status"] == "unavailable"
            unavailable = client.post(
                "/api/analyze", json={"text": text, "language": "en", "mode": mode}
            )
            assert unavailable.status_code == 503
            assert unavailable.json()["error"]["code"] == "ENGINE_UNAVAILABLE"
            response = client.post(
                "/api/analyze", json={"text": text, "language": "vi", "mode": mode}
            )
            assert response.status_code == 200, (mode, response.text)
            data = response.json()
            assert data["engine"] == engines["vi", mode]
            assert data["engine"]["status"] == "available"
            assert data["engine"]["model_revision"] == published_model_revision
            expected = [(name, "NAME", "medshield-crf"), (address, "ADDR", "medshield-crf")]
            expected_preview = text.replace(name, "[NAME_1]").replace(address, "[ADDR_1]")
            if mode == "hybrid":
                expected.insert(1, (dob, "DOB", "medshield-rules"))
                expected_preview = expected_preview.replace(dob, "[DOB_1]")
            entities = data["entities"]
            assert [
                (item["start"], item["end"], item["label"], item["source"]) for item in entities
            ] == [
                (text.index(value), text.index(value) + len(value), label, source)
                for value, label, source in expected
            ]
            assert data["redacted_text"] == expected_preview
            preview = client.post("/api/redact", json={"text": text, "entities": entities})
            assert preview.status_code == 200
            assert preview.json()["redacted_text"] == expected_preview


@pytest.mark.parametrize("mode", MODES)
def test_published_modes_preserve_unicode_outside_detected_spans(
    mode: str, published_model_revision: str
) -> None:
    """Check the independent Unicode note without imposing a recall target on NER."""
    name = normalize("NFD", "Nguyễn Ánh")
    text = f"🙂 Người bệnh {name}, sinh ngày 12/04/1988;\r\nmã BN-93012.\r\nHẹn tái khám 17/12."
    assert text.count("\r\n") == 2
    with TestClient(app) as client:
        response = client.post("/api/analyze", json={"text": text, "language": "vi", "mode": mode})
        assert response.status_code == 200, (mode, response.text)
        data = response.json()
        assert data["engine"]["mode"] == mode
        assert data["engine"]["status"] == "available"
        assert data["engine"].get("model_revision") == (
            None if mode == "rules" else published_model_revision
        )
        entities = data["entities"]
        previous_end = 0
        pattern: list[str] = []
        for item in entities:
            start, end = item["start"], item["end"]
            assert type(start) is int and type(end) is int
            assert previous_end <= start < end <= len(text)
            assert text[start:end] == text[start:end].strip()
            assert 0 <= item["score"] <= 1
            source, label = item["source"], item["label"]
            assert label in {"NAME", "DOB", "PHONE", "ID", "ADDR"}
            if mode == "ner" or source == "medshield-crf":
                assert label in {"NAME", "ADDR"} and source == "medshield-crf"
            else:
                assert source == "medshield-rules"
            pattern.extend((re.escape(text[previous_end:start]), rf"\[{label}_[1-9]\d*\]"))
            previous_end = end
        pattern.append(re.escape(text[previous_end:]))
        assert re.fullmatch("".join(pattern), data["redacted_text"])
        preview = client.post("/api/redact", json={"text": text, "entities": entities})
        assert preview.status_code == 200
        assert preview.json()["redacted_text"] == data["redacted_text"]
