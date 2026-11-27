# ml/meddies_train.py — Map publisher labels only in the provisional Meddies training cohort.
import json
import random
import re
from argparse import ArgumentParser
from collections import Counter, defaultdict
from hashlib import file_digest, sha256
from pathlib import Path
from typing import Any
from unicodedata import normalize

from ml.meddies_mapping_rules import CORRECTION_LABELS, remap_entities
from ml.meddies_qa import REVISION, SHARD_SHA256, cohort, text_hash, verified_rows

LABEL_MAP = {
    "human_name": "NAME",
    "phone_number": "PHONE",
    "address": "ADDR",
    "id_number": "ID",
}
WINDOW = 48
HARD_BOUNDARY = re.compile(r"[;|\r\n!?]|(?<![0-9])\.(?![0-9])|\.(?=\s+[^\W\d_])|(?<=\w),(?=\s)")
BIRTH = re.compile(
    r"\b(?:date of birth|birth date|dob|born|ngay sinh|nam sinh|"
    r"(?<!hoc )(?<!thi )sinh(?!\s+(?:vien|hoat|ly|hoc)))\b"
)
OTHER_DATE = re.compile(
    r"\b(?:tai kham|hen|ngay (?:kham|hen|lap|nhap|xuat|cap)|"
    r"(?:visit|appointment|admission|discharge) date)\b|[0-9]{1,4}[-/.][0-9]{1,2}"
)
AFTER = re.compile(r"^\s*[(\[]?\s*(?:dob|date of birth|ngay sinh|nam sinh)\b")


def _fold(text: str) -> str:
    """Fold case and Vietnamese accents for cue matching without changing source offsets."""
    return "".join(
        character
        for character in normalize("NFD", text.casefold().replace("đ", "d"))
        if not ("\u0300" <= character <= "\u036f")
    )


def birth_context(text: str, start: int, end: int) -> bool:
    """Check 48 original code points on each side without borrowing a previous date's cue."""
    left = HARD_BOUNDARY.split(_fold(text[max(0, start - WINDOW) : start]))[-1]
    right = _fold(text[end : end + WINDOW])
    cues = list(BIRTH.finditer(left))
    return bool((cues and not OTHER_DATE.search(left[cues[-1].end() :])) or AFTER.match(right))


def _valid_span(text: str, span: dict[str, Any]) -> bool:
    """Require verified publisher code-point bounds and the identical original surface."""
    start, end = span.get("start"), span.get("end")
    return (
        type(start) is int
        and type(end) is int
        and 0 <= start < end <= len(text)
        and text[start:end] == span.get("text")
        and bool(text[start:end].strip())
    )


def _publisher_entities(
    text: str, spans: list[dict[str, Any]], before: Counter[str], exclusions: Counter[str]
) -> list[dict[str, Any]]:
    """Map validated spans and omit conflicting overlaps rather than silently choosing a label."""
    candidates: set[tuple[int, int, str]] = set()
    for span in spans:
        category = span["category"]
        before[category] += 1
        label = LABEL_MAP.get(category)
        if category != "date" and label is None:
            exclusions["outside_scope"] += 1
            continue
        if not _valid_span(text, span):
            exclusions["invalid_offset_or_value"] += 1
            if category == "date":
                exclusions["date_invalid"] += 1
            continue
        start, end = span["start"], span["end"]
        if category == "date":
            if not birth_context(text, start, end):
                exclusions["date_without_birth_cue"] += 1
                continue
            label = "DOB"
        assert label is not None
        entry = (start, end, label)
        if entry in candidates:
            exclusions["duplicate_span"] += 1
        candidates.add(entry)
    kept = []
    for start, end, label in sorted(candidates):
        if any(
            a < end and start < b
            for a, b, other in candidates
            if (a, b, other) != (start, end, label)
        ):
            exclusions["overlapping_span"] += 1
            continue
        kept.append({"start": start, "end": end, "label": label})
    return kept


def map_note(
    text: str, spans: list[dict[str, Any]], before: Counter[str], exclusions: Counter[str]
) -> list[dict[str, Any]]:
    """Map publisher spans and apply the reviewed train-only corrections."""
    baseline = _publisher_entities(text, spans, before, exclusions)
    return remap_entities(text, baseline, Counter())


def prepare(shard: Path, private: Path, legacy_mapping: bool = False) -> dict[str, Any]:
    """Write provisional train and reviewer samples locally; publish only a count manifest."""
    reserved = {
        text_hash(row["text"])
        for row in verified_rows(shard)
        if cohort(row) == "evaluation_candidate"
    }
    before: Counter[str] = Counter()
    baseline_counts: Counter[str] = Counter()
    after: Counter[str] = Counter()
    exclusions: Counter[str] = Counter()
    corrections: Counter[str] = Counter()
    examples: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    rng = random.Random(20261126)
    seen, notes, zero_spans = set(reserved), 0, 0
    destination = private / "provisional-train.jsonl"
    with destination.open("x", encoding="utf-8", newline="\n") as output:
        for row in verified_rows(shard, annotations=True):
            if cohort(row) != "provisional_train":
                continue
            text = row["text"]
            digest = text_hash(text)
            if digest in seen:
                continue
            seen.add(digest)
            baseline = _publisher_entities(text, row["label"], before, exclusions)
            baseline_counts.update(entity["label"] for entity in baseline)
            entities = baseline if legacy_mapping else remap_entities(text, baseline, corrections)
            note_id = row["info"]["id"]
            output.write(
                json.dumps(
                    {"note_id": note_id, "text": text, "entities": entities}, ensure_ascii=False
                )
                + "\n"
            )
            notes += 1
            zero_spans += not entities
            for entity in entities:
                label = entity["label"]
                after[label] += 1
                rank = rng.randrange(after[label])
                if rank < 20:
                    start, end = entity["start"], entity["end"]
                    item = {
                        "note_id": note_id,
                        **entity,
                        "value": text[start:end],
                        "context": text[max(0, start - WINDOW) : end + WINDOW],
                    }
                    if len(examples[label]) < 20:
                        examples[label].append(item)
                    else:
                        examples[label][rank] = item
    sample_path = private / "train-mapping-samples.json"
    with sample_path.open("x", encoding="utf-8") as output:
        json.dump(examples, output, indent=2, ensure_ascii=False)
    with destination.open("rb") as stream:
        derived_hash = file_digest(stream, "sha256").hexdigest()
    total = before.total()
    result = {
        "revision": REVISION,
        "shard_sha256": SHARD_SHA256,
        "license": "CC-BY-NC-4.0",
        "status": "provisional_train_for_mapping_review_only",
        "training_pool_sha256": derived_hash,
        "notes": notes,
        "notes_without_mapped_spans": zero_spans,
        "publisher_spans": dict(before),
        "mapped_spans": dict(after),
        "exclusions": dict(exclusions),
        "total_drop_rate": (total - after.total()) / total,
        "date_kept": after["DOB"],
        "date_dropped": before["date"] - after["DOB"],
        "date_keep_rate": after["DOB"] / before["date"] if before["date"] else None,
        "birth_context_window_code_points": WINDOW,
        "private_review_samples_by_label": {label: len(rows) for label, rows in examples.items()},
        "review_samples_sha256": sha256(sample_path.read_bytes()).hexdigest(),
        "evaluation_labels_used": False,
        "training_started": False,
    }
    if not legacy_mapping:
        result.update(
            status="provisional_train_remapped_after_owner_review",
            baseline_mapped_spans=dict(baseline_counts),
            baseline_total_mapped_spans=baseline_counts.total(),
            total_mapped_spans=after.total(),
            mapping_corrections={
                rule: {"label": label, "action": action, "regions": corrections[rule]}
                for rule, (label, action) in CORRECTION_LABELS.items()
            },
        )
    return result


def main() -> None:
    """Run the pinned training-only mapper with private data output under artifacts/local."""
    parser = ArgumentParser(description="Ánh xạ nhãn Meddies cho nhóm train tạm.")
    parser.add_argument("shard", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--private-output", type=Path)
    parser.add_argument(
        "--legacy-mapping", action="store_true", help="Tái tạo bản train trước rà soát của Bước 2."
    )
    args = parser.parse_args()
    local_root = (Path(__file__).resolve().parents[1] / "artifacts/local").resolve()
    shard = args.shard.resolve()
    private = (args.private_output or (shard.parent / "step2")).resolve()
    if (
        not shard.is_relative_to(local_root)
        or not private.is_relative_to(local_root)
        or args.output.exists()
    ):
        parser.error("Shard phải trong artifacts/local và tệp số liệu đầu ra phải là tệp mới.")
    private.mkdir()
    result = prepare(shard, private, args.legacy_mapping)
    with args.output.open("x", encoding="utf-8", newline="\n") as output:
        output.write(json.dumps(result, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
