# ml/meddies_slices.py — Define Meddies gold span slices independently of model predictions.
import re
from collections import Counter
from collections.abc import Iterable
from unicodedata import category, normalize

from ml.bio import Span
from ml.dataset import Note
from ml.evaluation_slices import CORRECTION, RESIDENCE, _fold, _in_vn_numbering_plan

PHONE_ANCHOR = re.compile(r"\b(?:sdt|dt|dien thoai|lien he|lien lac|di dong|hotline|tel|phone)\b")
SLICES = (
    "name_lowercase",
    "id",
    "phone_outside_numbering_plan",
    "phone_distant_anchor",
    "dob",
    "dob_correction",
    "addr_residency_cue",
    "addr_no_residency_cue",
    "unaccented_note",
)


def _anchor_distance(prefix: str) -> int | None:
    """Measure the last same-line telephone cue distance in original code points."""
    pieces = [_fold(ch) for ch in prefix]
    offsets = [i for i, chars in enumerate(pieces) for _ in chars]
    matches = list(PHONE_ANCHOR.finditer("".join(pieces)))
    if not matches:
        return None
    end = offsets[matches[-1].end() - 1] + 1
    while end < len(prefix) and category(prefix[end]).startswith("M"):
        end += 1
    return len(prefix) - end


def memberships(note: Note, span: Span) -> set[str]:
    """Return all preregistered memberships for one span on the immutable input."""
    text = note.text
    value = text[span.start : span.end]
    prefix = re.split(r"[\r\n]", text[: span.start])[-1]
    slices = set()
    if span.label == "NAME" and value.islower():
        slices.add("name_lowercase")
    if span.label == "ID":
        slices.add("id")
    if span.label == "PHONE":
        if not _in_vn_numbering_plan(value):
            slices.add("phone_outside_numbering_plan")
        distance = _anchor_distance(prefix)
        if distance is not None and distance >= 14:
            slices.add("phone_distant_anchor")
    if span.label == "DOB":
        slices.add("dob")
        if CORRECTION.search(_fold(text)):
            slices.add("dob_correction")
    if span.label == "ADDR":
        slices.add(
            "addr_residency_cue"
            if RESIDENCE.search(_fold(prefix[-48:]))
            else "addr_no_residency_cue"
        )
    return slices


def support(notes: Iterable[Note]) -> dict[str, dict[str, int]]:
    """Count notes and exact gold spans by slice, including empty populations."""
    documents: Counter[str] = Counter()
    entities: Counter[str] = Counter()
    for note in notes:
        keys = set()
        unaccented = not any(
            ch in {"đ", "Đ"} or category(ch).startswith("M") for ch in normalize("NFD", note.text)
        )
        if unaccented:
            keys.add("unaccented_note")
            entities["unaccented_note"] += len(note.entities)
        for span in note.entities:
            found = memberships(note, span)
            keys.update(found)
            entities.update(found)
        documents.update(keys)
    return {key: {"notes": documents[key], "entities": entities[key]} for key in SLICES}
