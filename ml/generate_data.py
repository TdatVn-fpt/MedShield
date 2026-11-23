# ml/generate_data.py — Generate deterministic synthetic train and validation notes and manifest.
import json
from argparse import ArgumentParser
from hashlib import sha256
from pathlib import Path
from random import Random
from string import Formatter
from unicodedata import normalize

from ml.data_families import (
    CITY_NAMES,
    COMPLAINTS,
    ICD_CODES,
    TRAIN_FAMILIES,
    TRAIN_NAMES,
    TRAIN_STREETS,
    VALIDATION_FAMILIES,
    VALIDATION_NAMES,
    VALIDATION_STREETS,
    WARD_NAMES,
)
from ml.dataset import MANIFEST_FILENAME

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DATA_REVISION = "medshield-vi-synthetic-v2"
DEFAULT_SEED = 20261121
SLOT_LABELS = {
    "patient": "NAME",
    "relative": "NAME",
    "doctor": "NAME",
    "midline_patient": "NAME",
    "address": "ADDR",
    "old_address": "ADDR",
    "multiline_address": "ADDR",
    "birth": "DOB",
    "birth_year": "DOB",
    "phone": "PHONE",
    "record": "ID",
    "citizen": "ID",
}


def _values(
    rng: Random, names: tuple[str, ...], streets: tuple[str, ...], variant: int
) -> dict[str, str]:
    """Build one seeded set of invented names, contact fields and neutral context values."""
    patient, relative, doctor = rng.sample(names, 3)
    if variant == 0:
        patient = normalize("NFD", patient)
    street = f"{rng.randint(1, 170)} đường {rng.choice(streets)}"
    ward = f"phường {rng.choice(WARD_NAMES)}"
    city = f"TP. {rng.choice(CITY_NAMES)}"
    birth_year = str(rng.randint(1965, 2005))
    complaint = rng.choice(COMPLAINTS)
    contact_digits = f"{rng.randrange(10_000_000):07d}"
    phone = f"090{contact_digits}"
    if variant % 2:
        phone = f"+84 90 {contact_digits[:3]} {contact_digits[3:]}"
    return {
        "patient": patient,
        "relative": relative,
        "doctor": doctor,
        "midline_patient": patient.lower() if variant % 2 == 0 else patient,
        "address": f"{street}, {ward}, {city}",
        "multiline_address": f"{street},\r\n{ward}, {city}",
        "old_address": f"{rng.randint(2, 97)}/2 hẻm {rng.choice(streets)}, {ward}",
        "birth_year": birth_year,
        "birth": f"{rng.randint(1, 28):02d}/{rng.randint(1, 12):02d}/{birth_year}",
        "appointment": f"{rng.randint(1, 28):02d}/{rng.randint(1, 12):02d}",
        "phone": phone,
        "record": f"BN-{rng.randint(10000, 99999)}",
        "citizen": f"{rng.randrange(10**12):012d}",
        "queue": str(rng.randint(1, 50)),
        "oxygen": str(rng.randint(94, 100)),
        "dose": str(rng.choice((5, 10, 20, 250, 500))),
        "complaint": complaint,
        "symptom": f"Ghi nhận {complaint}.",
        "icd": rng.choice(ICD_CODES),
    }


def _render(
    note_id: str, family_id: str, template: str, values: dict[str, str]
) -> dict[str, object]:
    """Render source text and derive exact gold spans from annotated template fields."""
    parts: list[str] = []
    entities: list[dict[str, str | int]] = []
    position = 0
    for literal, field, _, _ in Formatter().parse(template):
        parts.append(literal)
        position += len(literal)
        if field is None:
            continue
        value = values[field]
        parts.append(value)
        end = position + len(value)
        if field in SLOT_LABELS:
            entities.append({"start": position, "end": end, "label": SLOT_LABELS[field]})
        position = end
    return {
        "note_id": note_id,
        "family_id": family_id,
        "text": "".join(parts),
        "entities": entities,
    }


def generate(data_dir: Path, seed: int) -> None:
    """Write train, validation and a manifest in stable UTF-8 bytes with SHA-256 hashes."""
    data_dir.mkdir(parents=True, exist_ok=True)
    splits: dict[str, object] = {}
    for split, families, count, names, streets in (
        ("train", TRAIN_FAMILIES, 6, TRAIN_NAMES, TRAIN_STREETS),
        ("validation", VALIDATION_FAMILIES, 5, VALIDATION_NAMES, VALIDATION_STREETS),
    ):
        rng = Random(f"{seed}:{split}")
        notes = [
            _render(
                f"{family_id}-{index + 1:02d}",
                family_id,
                template,
                _values(rng, names, streets, index),
            )
            for family_id, template in families.items()
            for index in range(count)
        ]
        filename = f"{split}.jsonl"
        payload = "".join(json.dumps(note, ensure_ascii=False) + "\n" for note in notes)
        data_bytes = payload.encode("utf-8")
        (data_dir / filename).write_bytes(data_bytes)
        splits[split] = {
            "file": filename,
            "notes": len(notes),
            "family_ids": sorted(families),
            "sha256": sha256(data_bytes).hexdigest(),
        }
    manifest = {
        "schema_version": 1,
        "revision": DATA_REVISION,
        "seed": seed,
        "provenance": {
            "generated_by": "Research/ML (Codex)",
            "source": "Ghi chú giả lập từ họ mẫu do dự án tạo.",
            "human_reviewed_notes": 0,
        },
        "splits": splits,
    }
    (data_dir / MANIFEST_FILENAME).write_bytes(
        (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    )


def main() -> None:
    """Parse generator options and create the two synthetic development splits."""
    parser = ArgumentParser(description="Sinh ghi chú giả lập train và validation.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()
    generate(args.data_dir, args.seed)


if __name__ == "__main__":
    main()
