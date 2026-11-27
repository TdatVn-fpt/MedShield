# ml/meddies_m_preflight_data.py — Prepare train-only splits for the fine-tuning pilot.
import json
from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from ml.bio import GOLD_LABELS
from ml.dataset import Note, parse_note
from ml.meddies_qa import REVISION, SHARD_SHA256

PREFLIGHT_SEED = 20261127
PREFLIGHT_SCOPE = "validation nội bộ phía train, không dùng tuyên bố"
REMAP_STATUS = "provisional_train_remapped_after_owner_review"
APPROVED_MAPPING_REPORT_SHA256 = "b3f565aaa37dea425b7fc731d364afdb25e953021105247d521f8223cacec9f3"


@dataclass(frozen=True, slots=True)
class PilotData:
    """Hold train-side subsets and a metadata-only description of their preparation."""

    train: list[Note]
    validation: list[Note]
    metadata: dict[str, Any]


def _prepared_note(raw: dict[str, Any], trimmed: Counter[str]) -> Note:
    """Align whitespace edges for BIO without changing the original note or source annotation."""
    text = raw["text"]
    entities = []
    for span in raw["entities"]:
        start, end, label = span["start"], span["end"], span["label"]
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text):
            raise ValueError("Biên nhãn train ngoài văn bản nguyên gốc.")
        value = text[start:end]
        if not value.strip():
            raise ValueError("Vùng train chỉ gồm khoảng trắng.")
        left = len(value) - len(value.lstrip())
        right = len(value) - len(value.rstrip())
        if left or right:
            trimmed[label] += 1
        entities.append({"start": start + left, "end": end - right, "label": label})
    return parse_note({**raw, "family_id": "unverified", "entities": entities})


def _rank_rows(raw: bytes, seed: int) -> tuple[list[bytes], list[bytes]]:
    """Allocate unique train-side IDs to disjoint seed-stable partitions and sort by rank."""
    groups: tuple[list[tuple[bytes, bytes]], list[tuple[bytes, bytes]]] = ([], [])
    seen = set()
    for line in raw.split(b"\n"):
        if not line:
            continue
        note_id = json.loads(line)["note_id"]
        if not isinstance(note_id, str) or not note_id or note_id in seen:
            raise ValueError("Mã ghi chú train thiếu hoặc bị trùng.")
        seen.add(note_id)
        rank = sha256(f"{seed}\0{note_id}".encode()).digest()
        partition = int.from_bytes(rank[:8], "big") % 5 == 0
        groups[partition].append((rank, line))
    return ([line for _, line in sorted(groups[0])], [line for _, line in sorted(groups[1])])


def load_pilot_data(
    pool: Path, manifest_path: Path, train_limit: int, validation_limit: int, seed: int
) -> PilotData:
    """Verify the remapped train pool and select separate fitting and internal-validation notes."""
    if train_limit < 1 or validation_limit < 1:
        raise ValueError("Mỗi tập chạy thử phải có ít nhất một ghi chú.")
    local = (Path(__file__).resolve().parents[1] / "artifacts/local/meddies").resolve()
    if not pool.resolve().is_relative_to(local) or pool.name != "provisional-train.jsonl":
        raise ValueError("Chỉ đọc nguồn train tạm trong artifacts/local/meddies.")
    manifest_bytes = manifest_path.read_bytes()
    manifest_digest = sha256(manifest_bytes).hexdigest()
    if manifest_digest != APPROVED_MAPPING_REPORT_SHA256:
        raise ValueError("Báo cáo ánh xạ không khớp SHA-256 của bản train đã qua QA.")
    manifest = json.loads(manifest_bytes)
    raw = pool.read_bytes()
    digest = sha256(raw).hexdigest()
    if (
        manifest.get("revision") != REVISION
        or manifest.get("shard_sha256") != SHARD_SHA256
        or manifest.get("status") != REMAP_STATUS
        or manifest.get("evaluation_labels_used") is not False
        or manifest.get("training_pool_sha256") != digest
    ):
        raise ValueError("Tệp train không khớp manifest ánh xạ đã kiểm.")
    train_rows, validation_rows = _rank_rows(raw, seed)
    if len(train_rows) + len(validation_rows) != manifest.get("notes"):
        raise ValueError("Số ghi chú train không khớp manifest.")
    if train_limit > len(train_rows) or validation_limit > len(validation_rows):
        raise ValueError("Số ghi chú chạy thử vượt số đã phân bổ trong train.")

    selected = {}
    split_metadata = {}
    for split, rows in (
        ("train", train_rows[:train_limit]),
        ("validation", validation_rows[:validation_limit]),
    ):
        trimmed: Counter[str] = Counter()
        selected[split] = [_prepared_note(json.loads(row), trimmed) for row in rows]
        support = Counter(span.label for note in selected[split] for span in note.entities)
        split_metadata[split] = {
            "notes": len(rows),
            "selection_sha256": sha256(b"\n".join(rows) + b"\n").hexdigest(),
            "support": {label: support[label] for label in sorted(GOLD_LABELS)},
            "whitespace_trimmed_by_label": dict(sorted(trimmed.items())),
        }
    return PilotData(
        selected["train"],
        selected["validation"],
        {
            "scope": PREFLIGHT_SCOPE,
            "seed": seed,
            "training_pool_sha256": digest,
            "mapping_manifest_sha256": manifest_digest,
            "splits": split_metadata,
            "patient_and_template_groups_verified": False,
            "evaluation_opened": False,
        },
    )
