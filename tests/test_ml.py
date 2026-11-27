# tests/test_ml.py — Verify the locked corpus and model behavior without scoring the test split.
import gc
import json
import re
import subprocess
import sys
from collections import defaultdict
from hashlib import sha256
from itertools import combinations
from pathlib import Path
from typing import TypedDict
from unicodedata import normalize

import pycrfsuite
import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from ml.bio import Span, decode_bio, encode_bio
from ml.features import extract_features
from ml.model import (
    METADATA_FILENAME,
    WEIGHTS_FILENAME,
    ModelLoadError,
    load_model,
    model_identity,
)
from ml.tokenization import tokenize

DATA = Path(__file__).resolve().parents[1] / "data"
LABELS = {"NAME", "DOB", "PHONE", "ID", "ADDR"}
SMOKE_NAME = "To\u0302 Vân Sa"
SMOKE_ADDRESS = "13 hẻm Nắng Vàng"
SMOKE_PHONE = "090 123 0461"
SMOKE_TEXT = (
    f"🧭 Họ tên: {SMOKE_NAME}.\r\nĐịa chỉ: {SMOKE_ADDRESS}.\r\n"
    f"Số điện thoại: {SMOKE_PHONE}. Tái khám 02/11."
)


class GoldEntity(TypedDict):
    """GoldEntity stores an exact half-open code point span and label."""

    start: int
    end: int
    label: str


class Note(TypedDict):
    """Note stores one synthetic document and its split family and gold spans."""

    note_id: str
    family_id: str
    text: str
    entities: list[GoldEntity]


def read_notes(path: Path) -> list[Note]:
    """read_notes loads one UTF-8 JSON object per physical line at the given path."""
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream]


def test_heldout_corpus_matches_manifest_and_span_contract() -> None:
    """Check the held-out artifact lock, exact schema, membership and span bounds."""
    manifest = json.loads((DATA / "test-manifest.json").read_text(encoding="utf-8"))
    corpus = DATA / "test.jsonl"
    payload = corpus.read_bytes().replace(b"\r\n", b"\n")
    assert payload.endswith(b"\n") and not payload.startswith(b"\xef\xbb\xbf")
    assert manifest["path"] == "data/test.jsonl"
    assert manifest["split"] == "test" and manifest["language"] == "vi"
    assert manifest["offset_unit"] == "unicode_code_point"
    assert manifest["digest"]["algorithm"] == "sha256"
    assert sha256(payload).hexdigest() == manifest["digest"]["value"]

    notes = read_notes(corpus)
    assert len(notes) == manifest["note_count"] == 20
    assert len({note["note_id"] for note in notes}) == len(notes)
    assert len({note["text"] for note in notes}) == len(notes)
    families: dict[str, list[str]] = defaultdict(list)
    labels: set[str] = set()
    for note in notes:
        assert set(note) == {"note_id", "family_id", "text", "entities"}
        assert note["note_id"].startswith("vi-test-")
        assert note["family_id"].startswith("qa_")
        text = note["text"]
        assert text.strip() and len(text) <= 50_000
        families[note["family_id"]].append(note["note_id"])
        previous_end = 0
        for entity in note["entities"]:
            assert set(entity) == {"start", "end", "label"}
            start, end, label = entity["start"], entity["end"], entity["label"]
            assert type(start) is int and type(end) is int
            assert previous_end <= start < end <= len(text)
            assert text[start:end].strip() == text[start:end]
            labels.add(label)
            previous_end = end

    declared = manifest["families"]
    assert len(declared) == len(families) == manifest["family_count"]
    assert len(families) >= 5
    assert families == {entry["family_id"]: entry["note_ids"] for entry in declared}
    assert labels == LABELS


def test_heldout_corpus_keeps_selected_unicode_and_negative_cases() -> None:
    """Verify literal decomposed names, embedded CRLF and contextual negative examples."""
    notes = {note["note_id"]: note for note in read_notes(DATA / "test.jsonl")}
    correction = notes["vi-test-011"]
    names = [
        correction["text"][item["start"] : item["end"]]
        for item in correction["entities"]
        if item["label"] == "NAME"
    ]
    assert names == ["Ngô Vy", "Ngo\u0302 Vy"]
    assert names[0] != names[1] and normalize("NFC", names[1]) == names[0]

    delivery = notes["vi-test-013"]
    address = next(item for item in delivery["entities"] if item["label"] == "ADDR")
    assert delivery["text"][address["start"] : address["end"]] == (
        "12 hẻm Hạt Nắng,\r\nphường Mây Lụa, TP. Tầm Ngân"
    )
    assert sum(not note["entities"] for note in notes.values()) == 5
    observation = notes["vi-test-018"]
    assert "J06.9" in observation["text"] and "18/12" in observation["text"]
    assert observation["entities"] == []


def template_skeleton(note: Note) -> str:
    """template_skeleton masks gold values and numbers to spot reused sentence templates."""
    parts: list[str] = []
    previous = 0
    for entity in note["entities"]:
        parts.extend((note["text"][previous : entity["start"]], f"<{entity['label']}>"))
        previous = entity["end"]
    parts.append(note["text"][previous:])
    skeleton = re.sub(r"\d+", "<number>", "".join(parts))
    return " ".join(normalize("NFC", skeleton).casefold().split())


def test_train_validation_and_test_are_pairwise_disjoint() -> None:
    """The three corpora share no family, note ID, literal text or masked template."""
    splits = {
        split: read_notes(DATA / f"{split}.jsonl") for split in ("train", "validation", "test")
    }
    for (left_name, left), (right_name, right) in combinations(splits.items(), 2):
        for key in ("family_id", "note_id", "text"):
            assert not {note[key] for note in left} & {note[key] for note in right}, (
                left_name,
                right_name,
                key,
            )
        left_templates = {template_skeleton(note) for note in left}
        right_templates = {template_skeleton(note) for note in right}
        assert not left_templates & right_templates, (left_name, right_name)


def smoke_span(value: str, label: str) -> Span:
    """smoke_span locates one known value in the fixture outside the locked split."""
    start = SMOKE_TEXT.index(value)
    return Span(start, start + len(value), label)


def test_bio_round_trip_preserves_original_offsets() -> None:
    """BIO reconstructs a decomposed name and address using offsets in the source."""
    spans = [
        smoke_span(SMOKE_NAME, "NAME"),
        smoke_span(SMOKE_ADDRESS, "ADDR"),
        smoke_span(SMOKE_PHONE, "PHONE"),
    ]
    tokens = tokenize(SMOKE_TEXT)
    tags = encode_bio(tokens, spans)
    assert [item.span for item in decode_bio(tokens, tags)] == spans[:2]
    assert SMOKE_TEXT[tokens[0].start : tokens[0].end] == "🧭"
    name_start = next(token for token in tokens if token.start == spans[0].start)
    assert SMOKE_TEXT[name_start.start : name_start.end] == "To\u0302"
    with pytest.raises(ValueError, match="token boundaries"):
        encode_bio(tokens, [Span(spans[0].start + 1, spans[0].end, "NAME")])


@pytest.fixture
def native_model(tmp_path: Path) -> Path:
    """native_model trains a real CRF on one isolated fixture for API wiring checks."""
    tokens = tokenize(SMOKE_TEXT)
    features = extract_features(SMOKE_TEXT, tokens)
    tags = encode_bio(tokens, [smoke_span(SMOKE_NAME, "NAME"), smoke_span(SMOKE_ADDRESS, "ADDR")])
    trainer = pycrfsuite.Trainer(verbose=False)
    trainer.append(features, tags)
    trainer.set_params({"c1": 0, "c2": 0.01, "max_iterations": 50})
    weights_path = tmp_path / WEIGHTS_FILENAME
    trainer.train(str(weights_path))
    identity = model_identity(weights_path.read_bytes())
    (tmp_path / METADATA_FILENAME).write_text(json.dumps(identity), encoding="utf-8")
    return tmp_path


def test_native_model_ner_and_hybrid_serve_real_spans(
    native_model: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A locally trained model drives NER and combines its spans with a rule-derived phone."""
    monkeypatch.setenv("MEDSHIELD_MODEL_DIR", str(native_model))
    probe = (
        "import runpy; from pathlib import Path; import sys; "
        "runpy.run_path('tests/test_ml.py')['assert_native_routes'](Path(sys.argv[1]))"
    )
    completed = subprocess.run(
        [sys.executable, "-X", "faulthandler", "-c", probe, str(native_model)],
        cwd=DATA.parent,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def assert_native_routes(native_model: Path) -> None:
    """assert_native_routes exercises real native inference inside an isolated process."""
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        engines = {(entry["language"], entry["mode"]): entry for entry in health.json()["engines"]}
        weights_path = native_model / WEIGHTS_FILENAME
        gc.collect()
        # Exercise the cached native tagger after its loader's local buffer is out of scope.
        allocation_pressure = [bytes([index]) * weights_path.stat().st_size for index in range(8)]
        expected = {
            ("NAME", SMOKE_NAME, "medshield-crf"),
            ("ADDR", SMOKE_ADDRESS, "medshield-crf"),
        }
        revision = "sha256:" + sha256(weights_path.read_bytes()).hexdigest()
        for mode in ("ner", "hybrid"):
            response = client.post(
                "/api/analyze", json={"text": SMOKE_TEXT, "language": "vi", "mode": mode}
            )
            assert response.status_code == 200
            result = response.json()
            assert result["engine"] == engines["vi", mode]
            assert result["engine"]["status"] == "available"
            assert result["engine"]["model_revision"] == revision
            entities = result["entities"]
            previous_end = 0
            for entity in entities:
                assert previous_end <= entity["start"] < entity["end"] <= len(SMOKE_TEXT)
                assert 0 <= entity["score"] <= 1
                previous_end = entity["end"]
            seen = {
                (entity["label"], SMOKE_TEXT[entity["start"] : entity["end"]], entity["source"])
                for entity in entities
            }
            if mode == "hybrid":
                expected.add(("PHONE", SMOKE_PHONE, "medshield-rules"))
            assert seen == expected
            preview = client.post("/api/redact", json={"text": SMOKE_TEXT, "entities": entities})
            assert preview.status_code == 200
            assert preview.json()["redacted_text"] == result["redacted_text"]
            assert result["redacted_text"].endswith("Tái khám 02/11.")
            assert result["redacted_text"].count("\r\n") == 2
            assert SMOKE_NAME not in result["redacted_text"]
            assert SMOKE_ADDRESS not in result["redacted_text"]
        del allocation_pressure


def test_native_model_rejects_weights_with_wrong_digest(native_model: Path) -> None:
    """Tampered weights fail compatibility checks before native inference is available."""
    weights_path = native_model / WEIGHTS_FILENAME
    weights_path.write_bytes(weights_path.read_bytes() + b"tampered")
    with pytest.raises(ModelLoadError, match="metadata"):
        load_model(native_model)
