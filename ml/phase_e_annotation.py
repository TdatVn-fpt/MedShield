# ml/phase_e_annotation.py — Prepare and reconcile blind Phase E annotation packets locally.
import json
import random
from argparse import ArgumentParser
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, replace
from hashlib import sha256
from pathlib import Path
from typing import Any

from ml.bio import Span
from ml.dataset import Note, parse_note
from ml.phase_e_intake import SLICES, IntakeError, _read_payload, _records, _rows, _safe_id
from ml.scoring import score_documents

SOURCE_FIELDS = {"note_id", "text", "family_id", "patient_group", "source_group", "slices"}
PACKET_MANIFEST = "packet-manifest.json"


@dataclass(frozen=True, slots=True)
class SourceNote:
    """Hold one approved unlabelled note and its preregistered sampling groups."""

    note: Note
    patient_group: str
    groups: frozenset[str]
    slices: tuple[str, ...]


def read_source(blob: bytes) -> dict[str, SourceNote]:
    """Load unlabelled source records and reject identifiers, spans and duplicate texts."""
    notes: dict[str, SourceNote] = {}
    texts: set[str] = set()
    for row in _rows(blob, "nguồn gán nhãn"):
        if set(row) != SOURCE_FIELDS:
            raise IntakeError("Nguồn chỉ được chứa văn bản, mã nhóm và lát đã đăng ký.")
        note_id, family, patient, origin = (
            _safe_id(row[k]) for k in ("note_id", "family_id", "patient_group", "source_group")
        )
        text, slices = row["text"], row["slices"]
        if not isinstance(text, str) or not text.strip() or len(text) > 50_000:
            raise IntakeError("Văn bản nguồn không hợp lệ.")
        try:
            text.encode("utf-8")
        except UnicodeError:
            raise IntakeError("Văn bản nguồn chứa mã Unicode không hợp lệ.") from None
        if (
            not isinstance(slices, list)
            or any(not isinstance(key, str) or key not in SLICES for key in slices)
            or len(set(slices)) != len(slices)
        ):
            raise IntakeError("Lát áp lực chưa đăng ký hoặc bị trùng.")
        if note_id in notes or text in texts:
            raise IntakeError("Nguồn bị trùng mã hoặc văn bản.")
        texts.add(text)
        groups = frozenset([f"source:{origin}", *(f"slice:{key}" for key in slices)])
        notes[note_id] = SourceNote(
            Note(note_id, family, text, ()), patient, groups, tuple(slices)
        )
    if not notes:
        raise IntakeError("Nguồn gán nhãn rỗng.")
    return notes


def choose_double_sample(notes: dict[str, SourceNote], seed: int) -> list[str]:
    """Cover every available source and slice, then fill to at least 20% using fixed randomness."""
    order = sorted(notes)
    random.Random(seed).shuffle(order)
    uncovered = set().union(*(item.groups for item in notes.values()))
    frequency = Counter(group for item in notes.values() for group in item.groups)
    picked: list[str] = []
    while uncovered:
        choice = max(
            order,
            key=lambda key: sum(1 / frequency[g] for g in sorted(notes[key].groups & uncovered)),
        )
        uncovered.difference_update(notes[choice].groups)
        picked.append(choice)
        order.remove(choice)
    target = max(0, (len(notes) + 4) // 5 - len(picked))
    return sorted(picked + order[:target])


def _manifest(source: bytes, notes: dict[str, SourceNote], seed: int) -> dict[str, Any]:
    """Bind the sampling procedure and selected opaque IDs to the exact approved source bytes."""
    return {
        "schema_version": 1,
        "source_sha256": sha256(source).hexdigest(),
        "seed": seed,
        "algorithm": "rarity_first_group_cover_then_seeded_fill_v1",
        "double_note_ids": choose_double_sample(notes, seed),
    }


def _write_jsonl(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    """Write a new UTF-8 JSONL file inside the configured private destination."""
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")


def prepare(source: bytes, directory: Path, seed: int) -> dict[str, int]:
    """Write separate blind packets; only the coordinator keeps the sampling manifest."""
    notes = read_source(source)
    manifest = _manifest(source, notes, seed)
    directory.mkdir()
    a, b = directory / "a-blind.jsonl", directory / "b-blind.jsonl"
    for path, subset in ((a, sorted(notes)), (b, manifest["double_note_ids"])):
        _write_jsonl(path, [{"note_id": key, "text": notes[key].note.text} for key in subset])
    with (directory / PACKET_MANIFEST).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(manifest, stream, indent=2)
        stream.write("\n")
    return {"source_notes": len(notes), "double_notes": len(manifest["double_note_ids"])}


def _annotations(
    blob: bytes, notes: dict[str, SourceNote], required: set[str]
) -> dict[str, list[dict[str, Any]]]:
    """Require the exact blind packet IDs and validate returned spans on unmodified source text."""
    loaded: dict[str, list[dict[str, Any]]] = {}
    for row in _rows(blob, "lượt gán nhãn"):
        key = _safe_id(row.get("note_id"))
        if set(row) != {"note_id", "entities"} or key not in required or key in loaded:
            raise IntakeError("Tệp trả về có bản ghi trùng, ngoài gói hoặc thừa trường.")
        entities = row["entities"]
        if not isinstance(entities, list) or any(
            not isinstance(span, dict) or set(span) != {"start", "end", "label"}
            for span in entities
        ):
            raise IntakeError("Vùng trả về chỉ gồm start, end và label.")
        note = notes[key].note
        try:
            parsed = parse_note({**row, "family_id": note.family_id, "text": note.text})
        except (ValueError, TypeError):
            raise IntakeError("Biên hoặc nhãn trả về không hợp lệ trên văn bản gốc.") from None
        loaded[key] = [{"start": s.start, "end": s.end, "label": s.label} for s in parsed.entities]
    if loaded.keys() != required:
        raise IntakeError("Thiếu bản ghi trả về, kể cả các ghi chú không có vùng.")
    return loaded


def reconcile(
    source: bytes, manifest_blob: bytes, first: bytes, second: bytes, destination: Path
) -> dict[str, Any]:
    """Save canonical separate annotations and disputed notes for the adjudicator."""
    notes = read_source(source)
    manifest = _read_payload(manifest_blob, PACKET_MANIFEST)
    if (
        not isinstance(manifest, dict)
        or type(manifest.get("seed")) is not int
        or manifest != _manifest(source, notes, manifest["seed"])
    ):
        raise IntakeError("Manifest chọn gán đôi không khớp nguồn đã ghi.")
    sample = set(manifest["double_note_ids"])
    a, b = _annotations(first, notes, set(notes)), _annotations(second, notes, sample)
    disagreements = sorted(key for key in sample if a[key] != b[key])
    iaa = score_documents(
        [
            replace(notes[key].note, entities=tuple(Span(**span) for span in a[key]))
            for key in sorted(sample)
        ],
        {key: [Span(**span) for span in b[key]] for key in sample},
        example_limit=0,
    )
    destination.mkdir()
    _write_jsonl(
        destination / "annotations-a.jsonl",
        [{"note_id": key, "entities": a[key]} for key in sorted(sample)],
    )
    _write_jsonl(
        destination / "annotations-b.jsonl",
        [{"note_id": key, "entities": b[key]} for key in sorted(sample)],
    )
    _write_jsonl(
        destination / "adjudication-input.jsonl",
        [
            {
                "note_id": key,
                "text": notes[key].note.text,
                "entities_a": a[key],
                "entities_b": b[key],
            }
            for key in disagreements
        ],
    )
    _write_jsonl(
        destination / "first-pass.jsonl",
        [
            {
                "note_id": key,
                "text": record.note.text,
                "family_id": record.note.family_id,
                "patient_group": record.patient_group,
                "slices": list(record.slices),
                "entities": a[key],
            }
            for key, record in sorted(notes.items())
        ],
    )
    return {
        "source_notes": len(notes),
        "double_notes": len(sample),
        "disputes": len(disagreements),
        "strict_iaa_micro": iaa["micro"],
        "strict_iaa_by_label": iaa["by_label"],
        "iaa_threshold_met": iaa["micro"]["f1"] >= 0.85,
    }


def finalize(directory: Path, adjudicated: bytes, output: Path) -> dict[str, int]:
    """Apply human decisions to disputed notes and write final gold in the intake schema."""
    first_pass = _rows((directory / "first-pass.jsonl").read_bytes(), "lượt gán thứ nhất")
    notes = read_source(
        _encode_jsonl(
            [
                {**{k: v for k, v in row.items() if k != "entities"}, "source_group": "qa"}
                for row in first_pass
            ]
        )
    )
    sample_ids = {
        _safe_id(row.get("note_id"))
        for row in _rows((directory / "annotations-b.jsonl").read_bytes(), "gán đôi")
    }
    a = _annotations((directory / "annotations-a.jsonl").read_bytes(), notes, sample_ids)
    b = _annotations((directory / "annotations-b.jsonl").read_bytes(), notes, sample_ids)
    disputes = {key for key in sample_ids if a[key] != b[key]}
    resolved = _annotations(adjudicated, notes, disputes)
    full = _annotations(
        _encode_jsonl(
            [{"note_id": row["note_id"], "entities": row["entities"]} for row in first_pass]
        ),
        notes,
        set(notes),
    )
    if any(full[key] != a[key] for key in sample_ids):
        raise IntakeError("Nhãn lượt đầu thay đổi từ khi chuẩn bị gán đôi.")
    rows = [
        {**row, "entities": resolved.get(row["note_id"], full[row["note_id"]])}
        for row in first_pass
    ]
    _records(_encode_jsonl(rows), "bản sau phân xử")
    _write_jsonl(output, rows)
    return {"source_notes": len(rows), "double_notes": len(sample_ids), "disputes": len(disputes)}


def _encode_jsonl(rows: Sequence[dict[str, Any]]) -> bytes:
    """Encode in-memory records for validation without creating a temporary text file."""
    return "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows).encode("utf-8")


def main() -> None:
    """Run local packet preparation or reconciliation without logging note contents."""
    parser = ArgumentParser(description="Chuẩn bị và đối chiếu hai lượt gán nhãn mù Phase E.")
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("prepare")
    build.add_argument("source", type=Path)
    build.add_argument("directory", type=Path)
    build.add_argument("--seed", type=int, required=True)
    collect = commands.add_parser("reconcile")
    for field in ("source", "manifest", "first", "second", "directory"):
        collect.add_argument(field, type=Path)
    finish = commands.add_parser("finalize")
    for field in ("directory", "adjudicated", "output"):
        finish.add_argument(field, type=Path)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            result = prepare(args.source.read_bytes(), args.directory, args.seed)
        elif args.command == "reconcile":
            result = reconcile(
                args.source.read_bytes(),
                args.manifest.read_bytes(),
                args.first.read_bytes(),
                args.second.read_bytes(),
                args.directory,
            )
        else:
            result = finalize(args.directory, args.adjudicated.read_bytes(), args.output)
        print(json.dumps(result))
    except IntakeError as exc:
        parser.exit(1, f"Phase E: {exc}\n")
    except (OSError, UnicodeError, KeyError):
        parser.exit(1, "Phase E: Tệp thiếu, không hợp lệ hoặc đầu ra đã có.\n")


if __name__ == "__main__":
    main()
