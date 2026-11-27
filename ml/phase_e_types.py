# ml/phase_e_types.py — Share Phase E record definitions across private local commands.
from dataclasses import dataclass

from ml.dataset import Note

SLICES = {
    "phone_outside_plan": "PHONE",
    "dob_correction": "DOB",
    "name_lowercase": "NAME",
    "addr_delivery": "ADDR",
    "unaccented_text": None,
}


class IntakeError(ValueError):
    """Report a sanitized Phase E validation error without including annotation data."""


@dataclass(frozen=True, slots=True)
class Record:
    """Represent one Phase E note with opaque patient grouping and preregistered slices."""

    note: Note
    patient_group: str
    slices: frozenset[str]
