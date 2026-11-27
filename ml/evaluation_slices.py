# ml/evaluation_slices.py — Declare diagnostic span populations apart from recognizer logic.
import re
from unicodedata import category, normalize

import phonenumbers

from ml.bio import Span
from ml.dataset import Note

SLICE_LABELS = {
    "phone_in_numbering_plan": "PHONE",
    "phone_outside_numbering_plan": "PHONE",
    "dob_correction": "DOB",
    "dob_other": "DOB",
    "addr_residency_cue": "ADDR",
    "addr_no_residency_cue": "ADDR",
    "name_lowercase": "NAME",
    "name_other_case": "NAME",
}
CORRECTION = re.compile(
    r"\b(?:dinh chinh|cai chinh|hieu chinh|"
    r"sua (?:lai|sai|ngay|nam)|(?:doi|chuyen|chinh sua) (?:ngay|nam|thong tin)|"
    r"thay doi (?:ngay|nam|thong tin))\b"
)
RESIDENCE = re.compile(
    r"\b(?:dia chi|cu tru|thuong tru|tam tru|que quan|noi o|ho khau|hktt)\b"
    r"|(?<!\w)d/c(?=\W|$)"
)
FIELD_BREAK = re.compile(r"[;|!?]|(?<!\d)\.(?!\d|[ \t]*$)")


def _fold(value: str) -> str:
    """Lowercase and strip Vietnamese accents for diagnostic context labels only."""
    decomposed = normalize("NFD", value.casefold().replace("đ", "d"))
    return "".join(char for char in decomposed if not category(char).startswith("M"))


def _in_vn_numbering_plan(value: str) -> bool:
    """Ask libphonenumber whether a phone surface matches Vietnamese numbering metadata."""
    candidate = value.strip()
    if candidate.startswith("(+84)"):
        candidate = "+84" + candidate[5:]
    try:
        number = phonenumbers.parse(candidate, "VN")
    except phonenumbers.NumberParseException:
        return False
    return phonenumbers.is_valid_number_for_region(number, "VN")


def classify_span(note: Note, span: Span) -> str | None:
    """Assign the gold or predicted span to exactly one population for its diagnostic label."""
    surface = note.text[span.start : span.end]
    if span.label == "PHONE":
        return (
            "phone_in_numbering_plan"
            if _in_vn_numbering_plan(surface)
            else "phone_outside_numbering_plan"
        )
    if span.label == "NAME":
        return "name_lowercase" if surface.islower() else "name_other_case"
    if span.label == "DOB":
        return "dob_correction" if CORRECTION.search(_fold(note.text)) else "dob_other"
    if span.label == "ADDR":
        prefix = _fold(note.text[max(0, span.start - 100) : span.start])
        current_field = FIELD_BREAK.split(prefix)[-1]
        recent_words = " ".join(current_field.split()[-8:])
        return "addr_residency_cue" if RESIDENCE.search(recent_words) else "addr_no_residency_cue"
    return None
