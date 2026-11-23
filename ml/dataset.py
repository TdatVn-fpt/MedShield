# ml/dataset.py — Read and validate the synthetic train and validation dataset.
import json
from dataclasses import dataclass
from hashlib import sha256
from itertools import pairwise
from pathlib import Path

from ml.bio import GOLD_LABELS, Span

MANIFEST_FILENAME = "train-validation-manifest.json"


@dataclass(frozen=True, slots=True)
class Note:
    """Note stores one source text and its sorted non-overlapping gold spans."""

    note_id: str
    family_id: str
    text: str
    entities: tuple[Span, ...]


@dataclass(frozen=True, slots=True)
class Dataset:
    """Dataset carries only the development splits and their verified manifest identity."""

    train: list[Note]
    validation: list[Note]
    revision: str
    seed: int
    manifest_sha256: str
    split_sha256: dict[str, str]


def parse_note(raw: object) -> Note:
    """Validate one JSONL record, including strict half-open Unicode span bounds."""
    if not isinstance(raw, dict):
        raise ValueError("Dataset note must be an object.")
    note_id, family_id, text = (raw.get(key) for key in ("note_id", "family_id", "text"))
    if not isinstance(note_id, str) or not note_id:
        raise ValueError("Invalid dataset note ID.")
    if not isinstance(family_id, str) or not family_id:
        raise ValueError("Invalid dataset family ID.")
    if not isinstance(text, str) or not text.strip() or len(text) > 50_000:
        raise ValueError(f"Invalid text length in note {note_id}.")
    entities = raw.get("entities")
    if not isinstance(entities, list) or len(entities) > 2_000:
        raise ValueError(f"Invalid entity list in note {note_id}.")
    spans: list[Span] = []
    for entity in entities:
        if not isinstance(entity, dict):
            raise ValueError(f"Invalid gold entity in note {note_id}.")
        start, end, label = (entity.get(key) for key in ("start", "end", "label"))
        if (
            type(start) is not int
            or type(end) is not int
            or not 0 <= start < end <= len(text)
            or label not in GOLD_LABELS
            or text[start:end] != text[start:end].strip()
        ):
            raise ValueError(f"Invalid gold span in note {note_id}.")
        spans.append(Span(start, end, label))
    spans.sort(key=lambda span: span.start)
    if any(left.end > right.start for left, right in pairwise(spans)):
        raise ValueError(f"Overlapping gold spans in note {note_id}.")
    return Note(note_id, family_id, text, tuple(spans))


def load_dataset(data_dir: Path) -> Dataset:
    """Open only train and validation and verify hashes, declared families and duplicates."""
    manifest_bytes = (data_dir / MANIFEST_FILENAME).read_bytes()
    manifest = json.loads(manifest_bytes)
    if (
        not isinstance(manifest, dict)
        or manifest.get("schema_version") != 1
        or not isinstance(manifest.get("revision"), str)
        or type(manifest.get("seed")) is not int
        or not isinstance(manifest.get("splits"), dict)
    ):
        raise ValueError("Invalid development dataset manifest.")

    notes_by_split: dict[str, list[Note]] = {}
    hashes: dict[str, str] = {}
    seen_ids: set[str] = set()
    seen_texts: set[str] = set()
    seen_families: set[str] = set()
    for split in ("train", "validation"):
        filename = f"{split}.jsonl"
        raw = (data_dir / filename).read_bytes()
        digest = sha256(raw).hexdigest()
        record = manifest["splits"].get(split)
        if (
            not isinstance(record, dict)
            or record.get("file") != filename
            or record.get("sha256") != digest
        ):
            raise ValueError(f"Dataset manifest does not match {filename}.")
        notes = [parse_note(json.loads(line)) for line in raw.decode("utf-8").split("\n") if line]
        families = {note.family_id for note in notes}
        declared_families = record.get("family_ids")
        if (
            not notes
            or len(notes) != record.get("notes")
            or not isinstance(declared_families, list)
            or sorted(families) != declared_families
            or seen_families & families
        ):
            raise ValueError(f"Invalid split size or family membership in {filename}.")
        for note in notes:
            if note.note_id in seen_ids or note.text in seen_texts:
                raise ValueError(f"Duplicate note ID or text in {filename}.")
            seen_ids.add(note.note_id)
            seen_texts.add(note.text)
        seen_families.update(families)
        notes_by_split[split], hashes[split] = notes, digest
    return Dataset(
        notes_by_split["train"],
        notes_by_split["validation"],
        manifest["revision"],
        manifest["seed"],
        sha256(manifest_bytes).hexdigest(),
        hashes,
    )
