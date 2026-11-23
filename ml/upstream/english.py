# ml/upstream/english.py — Load the locked synthetic English corpus and score redaction regions.
import json
from hashlib import sha256
from pathlib import Path
from typing import TypedDict

from ml.upstream.adapters import Span
from ml.upstream.regions import contiguous_positions, covered_positions

CORPUS = Path("data/english.jsonl")
REVISION = "en-g2-v1"
CORPUS_SHA256 = "100083a44fb393c1661c77c69a13f41d52907a3e2d7cfd94f1c331d1089d879a"


class GoldSpan(TypedDict):
    """GoldSpan carries a BA-annotated half-open span and its original label."""

    start: int
    end: int
    label: str


class EnglishNote(TypedDict):
    """EnglishNote describes one verified JSONL record from the synthetic English corpus."""

    note_id: str
    family_id: str
    text: str
    entities: list[GoldSpan]


class RegionExample(TypedDict):
    """RegionExample identifies a contiguous false-positive or missed region on synthetic text."""

    note_id: str
    kind: str
    label: str
    text: str
    start: int
    end: int


def load_corpus() -> list[EnglishNote]:
    """load_corpus reads only the approved 16-note revision, preserving decoded note characters."""
    raw = CORPUS.read_bytes().replace(b"\r\n", b"\n")
    if sha256(raw).hexdigest() != CORPUS_SHA256:
        raise ValueError("English corpus hash differs from the locked BA revision.")
    return [json.loads(line) for line in raw.decode("utf-8").split("\n") if line]


def corpus_metadata(notes: list[EnglishNote]) -> dict[str, object]:
    """corpus_metadata records the common scope and provenance without duplicating the notes."""
    return {
        "revision": REVISION,
        "sha256": CORPUS_SHA256,
        "file": CORPUS.as_posix(),
        "seed": None,
        "provenance": "BA hand-authored and annotated synthetic English notes; data/english.md",
        "human_reviewed_notes": 0,
        "split": "english_benchmark",
        "notes": len(notes),
        "gold_entities": sum(len(note["entities"]) for note in notes),
        "note_ids": [note["note_id"] for note in notes],
        "family_ids": [note["family_id"] for note in notes],
        "excluded": [],
    }


def _ratio(numerator: int, denominator: int) -> float:
    """Return a metric ratio, using zero for a zero denominator."""
    return numerator / denominator if denominator else 0.0


def gold_positions(note: EnglishNote) -> set[int]:
    """gold_positions projects a note's original gold spans to covered code points."""
    return covered_positions(
        note["text"], ((span["start"], span["end"]) for span in note["entities"])
    )


def score_regions(
    notes: list[EnglishNote], predictions: dict[str, list[Span]]
) -> dict[str, object]:
    """score_regions computes micro coverage, residual notes and synthetic error examples."""
    if predictions.keys() != {note["note_id"] for note in notes}:
        raise ValueError("Engine predictions differ from the locked set of note IDs.")

    tp = fp = fn = notes_with_fn = 0
    examples: dict[str, list[RegionExample]] = {"FP": [], "FN": []}
    for note in notes:
        note_id, text = note["note_id"], note["text"]
        gold = gold_positions(note)
        predicted = covered_positions(text, predictions[note_id])
        extra, missed = predicted - gold, gold - predicted
        tp += len(gold & predicted)
        fp += len(extra)
        fn += len(missed)
        notes_with_fn += bool(missed)
        for kind, errors in (("FP", extra), ("FN", missed)):
            if errors and len(examples[kind]) < 3:
                span = contiguous_positions(errors)[0]
                start, end = span["start"], span["end"]
                examples[kind].append(
                    {
                        "note_id": note_id,
                        "kind": kind,
                        "label": "REGION",
                        "text": text[start:end],
                        "start": start,
                        "end": end,
                    }
                )

    return {
        "micro": {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": _ratio(tp, tp + fp),
            "recall": _ratio(tp, tp + fn),
            "f1": _ratio(2 * tp, 2 * tp + fp + fn),
            "support": tp + fn,
        },
        "notes_with_fn": notes_with_fn,
        "examples": examples["FP"] + examples["FN"],
    }
