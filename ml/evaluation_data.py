# ml/evaluation_data.py — Validate the frozen Vietnamese evaluation corpus and its QA manifest.
import codecs
import json
from collections import defaultdict
from hashlib import sha256
from pathlib import Path
from typing import Any

from ml.dataset import Note, parse_note

TEST_FILENAME = "test.jsonl"
TEST_MANIFEST_FILENAME = "test-manifest.json"


def read_object(path: Path) -> dict[str, Any]:
    """Read an artifact JSON file and require a root object."""
    value = json.loads(path.read_bytes())
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object.")
    return value


def load_heldout(data_dir: Path) -> tuple[list[Note], dict[str, Any]]:
    """Verify the QA-locked canonical hash and read notes without normalizing their text."""
    manifest = read_object(data_dir / TEST_MANIFEST_FILENAME)
    if (
        manifest.get("schema_version") != 1
        or manifest.get("split") != "test"
        or manifest.get("language") != "vi"
        or manifest.get("path") != f"data/{TEST_FILENAME}"
        or manifest.get("synthetic") is not True
        or manifest.get("offset_unit") != "unicode_code_point"
    ):
        raise ValueError("Invalid synthetic Vietnamese test manifest.")

    raw = (data_dir / TEST_FILENAME).read_bytes().replace(b"\r\n", b"\n")
    digest = manifest.get("digest")
    if (
        not isinstance(digest, dict)
        or digest.get("algorithm") != "sha256"
        or digest.get("value") != sha256(raw).hexdigest()
        or not raw.endswith(b"\n")
        or raw.startswith(codecs.BOM_UTF8)
    ):
        raise ValueError("Vietnamese test corpus does not match the QA-locked SHA-256.")

    notes = [parse_note(json.loads(line)) for line in raw.decode("utf-8").split("\n")[:-1]]
    families: dict[str, list[str]] = defaultdict(list)
    for note in notes:
        families[note.family_id].append(note.note_id)
    locked_families = [
        {"family_id": family_id, "note_ids": members} for family_id, members in families.items()
    ]
    if (
        not notes
        or len(notes) != manifest.get("note_count")
        or len({note.note_id for note in notes}) != len(notes)
        or len(families) != manifest.get("family_count")
        or locked_families != manifest.get("families")
    ):
        raise ValueError("Vietnamese test corpus does not match the QA-locked family manifest.")
    return notes, manifest
