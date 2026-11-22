# tests/test_evaluation.py — Independently verify scoring and artifact availability contracts.
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api import controllers
from apps.api.main import app
from ml.bio import Span
from ml.dataset import Note
from ml.evaluation_data import TEST_FILENAME, TEST_MANIFEST_FILENAME, load_heldout
from ml.scoring import score_documents
from ml.upstream.english import EnglishNote, score_regions
from ml.upstream.regions import covered_positions


def test_exact_span_and_label_scorer_matches_hand_calculation() -> None:
    """A shifted boundary and a wrong label each create an FP and an FN."""
    notes = [
        Note("a", "qa-a", "🙂 An A.\r\nMã XY", (Span(2, 6, "NAME"), Span(12, 14, "ID"))),
        Note("b", "qa-b", "Bình 1980", (Span(0, 4, "NAME"), Span(5, 9, "DOB"))),
        Note("c", "qa-c", "O2 98", ()),
    ]
    predictions = {
        "a": [Span(2, 4, "NAME"), Span(12, 14, "ID"), Span(9, 11, "ADDR")],
        "b": [Span(0, 4, "ADDR"), Span(5, 9, "DOB")],
        "c": [Span(3, 5, "PHONE")],
    }
    result = score_documents(notes, predictions, example_limit=4)
    assert result["notes"] == 3
    assert result["gold_entities"] == 4
    assert result["notes_with_fn"] == 2
    assert result["micro"] == {
        "support": 4,
        "tp": 2,
        "fp": 4,
        "fn": 2,
        "precision": pytest.approx(1 / 3),
        "recall": 0.5,
        "f1": 0.4,
    }
    by_label = result["by_label"]
    assert {
        label: (row["support"], row["tp"], row["fp"], row["fn"]) for label, row in by_label.items()
    } == {
        "NAME": (2, 0, 1, 2),
        "DOB": (1, 1, 0, 0),
        "PHONE": (0, 0, 1, 0),
        "ID": (1, 1, 0, 0),
        "ADDR": (0, 0, 2, 0),
    }
    for label, row in by_label.items():
        expected = 1.0 if label in {"DOB", "ID"} else 0.0
        assert (row["precision"], row["recall"], row["f1"]) == (expected,) * 3
    assert {
        (item["note_id"], item["kind"], item["label"], item["text"]) for item in result["examples"]
    } == {
        ("a", "FP", "NAME", "An"),
        ("a", "FP", "ADDR", "Mã"),
        ("b", "FP", "ADDR", "Bình"),
        ("c", "FP", "PHONE", "98"),
        ("a", "FN", "NAME", "An A"),
        ("b", "FN", "NAME", "Bình"),
    }


def test_scorer_handles_empty_denominators_and_keeps_notes_separate() -> None:
    """Equal offsets in different notes never match, and empty ratios are zero."""
    span = Span(0, 2, "NAME")
    first = Note("a", "qa-a", "An", (span,))
    second = Note("b", "qa-b", "Vy", ())
    empty = score_documents([second], {"b": []})
    assert empty["notes"] == 1
    assert empty["notes_with_fn"] == 0
    assert all(value == 0 for value in empty["micro"].values())
    assert empty["examples"] == []

    result = score_documents([first, second], {"a": [], "b": [span, span]}, example_limit=0)
    micro = result["micro"]
    assert (micro["tp"], micro["fp"], micro["fn"], micro["support"]) == (0, 1, 1, 1)
    assert result["notes_with_fn"] == 1
    assert result["examples"] == []


def test_scorer_requires_predictions_even_for_an_empty_gold_note() -> None:
    """A missing prediction document is rejected instead of silently reducing the denominator."""
    note = Note("a", "qa-a", "Ghi chú giả lập.", ())
    with pytest.raises(ValueError, match="every unique gold note ID"):
        score_documents([note], {})


def test_region_scorer_counts_unicode_positions_once_and_ignores_whitespace() -> None:
    """A combining mark can be missed and duplicated covered positions count only once."""
    note: EnglishNote = {
        "note_id": "a",
        "family_id": "qa-en",
        "text": "🧪A\r\nB\u0301 C",
        "entities": [{"start": 1, "end": 6, "label": "NAME"}],
    }
    spans = [(3, 5), (4, 5), (7, 8)]
    assert covered_positions(note["text"], [(1, 6)]) == {1, 4, 5}
    assert covered_positions(note["text"], spans) == {4, 7}
    result = score_regions([note], {"a": spans})
    assert result["notes_with_fn"] == 1
    assert result["micro"] == {
        "support": 3,
        "tp": 1,
        "fp": 1,
        "fn": 2,
        "precision": 0.5,
        "recall": pytest.approx(1 / 3),
        "f1": 0.4,
    }


def test_heldout_reader_accepts_record_newlines_but_rejects_byte_drift(tmp_path: Path) -> None:
    """Canonicalize physical CRLF without changing text and reject a changed corpus copy."""
    source = Path(__file__).resolve().parents[1] / "data"
    expected, _ = load_heldout(source)
    manifest = (source / TEST_MANIFEST_FILENAME).read_bytes()
    payload = (source / TEST_FILENAME).read_bytes().replace(b"\r\n", b"\n")
    (tmp_path / TEST_MANIFEST_FILENAME).write_bytes(manifest)
    copy = tmp_path / TEST_FILENAME
    copy.write_bytes(payload.replace(b"\n", b"\r\n"))
    assert load_heldout(tmp_path)[0] == expected
    copy.write_bytes(payload.replace(b"vi-test-001", b"vi-test-999", 1))
    with pytest.raises(ValueError, match="QA-locked SHA-256"):
        load_heldout(tmp_path)


@pytest.mark.parametrize(
    "contents",
    [None, "{", '{"results":"not-a-list"}'],
    ids=["missing", "malformed-json", "invalid-results"],
)
def test_evaluation_unavailable_for_missing_or_invalid_artifact(
    contents: str | None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing or malformed evaluation file returns a safe unavailable response."""
    path = tmp_path / "evaluation.json"
    if contents is not None:
        path.write_text(contents, encoding="utf-8")
    monkeypatch.setattr(controllers, "EVALUATION_PATH", path)
    with TestClient(app) as client:
        response = client.get("/api/evaluation")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {"status": "unavailable", "reason": "Chưa có kết quả đánh giá."}
