# ml/phase_e_intake.py — Verify and seal Phase E intake inside its private data boundary.
import json
from argparse import ArgumentParser
from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path
from typing import Any

from ml.bio import GOLD_LABELS
from ml.dataset import Note, parse_note
from ml.phase_e_groups import GroupPair, check_groups
from ml.phase_e_types import SLICES as SLICES
from ml.phase_e_types import IntakeError as IntakeError
from ml.phase_e_types import Record as Record
from ml.scoring import score_documents

PROTOCOL = Path(__file__).resolve().parents[1] / "docs/phase-e.md"
FILES = (
    "provenance.json",
    "train-groups.jsonl",
    "validation.jsonl",
    "test.jsonl",
    "annotations-a.jsonl",
    "annotations-b.jsonl",
    "adjudication.jsonl",
    "source.jsonl",
    "packet-manifest.json",
)
MANIFEST_NAME = "phase-e-lock.json"


def _safe_id(value: object) -> str:
    """Validate an opaque identifier without ever echoing it in an error."""
    if not isinstance(value, str) or not 1 <= len(value) <= 128:
        raise IntakeError("Định danh nhóm hoặc vai trò không hợp lệ.")
    if not value.isascii() or any(not (char.isalnum() or char in "-_") for char in value):
        raise IntakeError("Định danh nhóm hoặc vai trò phải dùng mã ASCII.")
    return value


def _read_payload(blob: bytes, filename: str) -> Any:
    """Parse JSON bytes without including private values in exceptions."""
    try:
        return json.loads(blob.decode("utf-8"))
    except (ValueError, UnicodeError):
        raise IntakeError(f"JSON UTF-8 không hợp lệ: {filename}.") from None


def _rows(blob: bytes, filename: str) -> list[dict[str, Any]]:
    """Read UTF-8 LF JSONL objects and reject blank internal rows."""
    if not blob:
        return []
    if not blob.endswith(b"\n") or b"\r" in blob:
        raise IntakeError(f"JSONL phải dùng UTF-8 và LF: {filename}.")
    rows = []
    for line in blob[:-1].split(b"\n"):
        row = _read_payload(line, filename)
        if not isinstance(row, dict):
            raise IntakeError(f"Bản ghi không phải đối tượng: {filename}.")
        rows.append(row)
    return rows


def _provenance(blob: bytes) -> dict[str, Any]:
    """Validate required provenance attestations; the reviewer verifies their authenticity."""
    value = _read_payload(blob, FILES[0])
    if not isinstance(value, dict) or type(value.get("schema_version")) is not int:
        raise IntakeError("Thiếu metadata nguồn Phase E.")
    source_types = ("independent_generator", "approved_surrogate")
    if value["schema_version"] != 1 or value.get("source_type") not in source_types:
        raise IntakeError("Nguồn phải là quy trình sinh độc lập hoặc ghi chú đã thay surrogate.")
    for field in ("source_evidence_sha256", "owner_approval_sha256", "packet_manifest_sha256"):
        digest = value.get(field)
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(char not in "0123456789abcdef" for char in digest)
        ):
            raise IntakeError(f"Thiếu SHA-256 hợp lệ: {field}.")
    for field in ("independent_of_detection", "human_blind_double_annotation"):
        if value.get(field) is not True:
            raise IntakeError(f"Thiếu xác nhận bắt buộc: {field}.")
    roles = [_safe_id(value.get(field)) for field in ("annotator_a", "annotator_b", "adjudicator")]
    if len(set(roles)) != len(roles):
        raise IntakeError("Hai người gán nhãn và trọng tài cần là ba người khác nhau.")
    reviewed = value.get("participant_reviewed_count")
    if type(reviewed) is not int or reviewed < 0:
        raise IntakeError("Cần số ghi chú test mà chủ dự án thực sự đã rà soát.")
    return value


def _records(blob: bytes, filename: str) -> dict[str, Record]:
    """Check gold spans, opaque IDs, unique texts and the meaning of declared slices."""
    notes: dict[str, Record] = {}
    texts: set[str] = set()
    for row in _rows(blob, filename):
        try:
            note = parse_note(row)
        except (TypeError, ValueError):
            raise IntakeError(f"Vùng vàng hoặc văn bản không hợp lệ: {filename}.") from None
        _safe_id(note.note_id)
        _safe_id(note.family_id)
        patient = _safe_id(row.get("patient_group"))
        slices = row.get("slices")
        if (
            not isinstance(slices, list)
            or any(not isinstance(name, str) or name not in SLICES for name in slices)
            or len(set(slices)) != len(slices)
        ):
            raise IntakeError(f"Lát cắt không hợp lệ: {filename}.")
        labels = {entity.label for entity in note.entities}
        if any(SLICES[name] and SLICES[name] not in labels for name in slices):
            raise IntakeError(f"Lát cắt không có nhãn vàng tương ứng: {filename}.")
        if note.note_id in notes or note.text in texts:
            raise IntakeError(f"Trùng mã ghi chú hoặc văn bản: {filename}.")
        texts.add(note.text)
        notes[note.note_id] = Record(note, patient, frozenset(slices))
    return notes


def _annotation(blob: bytes, filename: str, test: dict[str, Record]) -> dict[str, Note]:
    """Validate private blind annotations against the same unmodified locked note text."""
    notes: dict[str, Note] = {}
    for row in _rows(blob, filename):
        note_id = _safe_id(row.get("note_id"))
        if set(row) != {"note_id", "entities"} or note_id not in test or note_id in notes:
            raise IntakeError(f"Bản ghi gán nhãn trùng, thừa trường hoặc ngoài tập: {filename}.")
        base = test[note_id].note
        try:
            notes[note_id] = parse_note(dict(row, family_id=base.family_id, text=base.text))
        except (TypeError, ValueError):
            raise IntakeError(f"Biên gán nhãn không hợp lệ: {filename}.") from None
    return notes


def read_train_groups(train_blob: bytes) -> set[GroupPair]:
    """Read the training inventory with validated and opaque patient and family keys."""
    train = _rows(train_blob, FILES[1])
    if not train or any(set(row) != {"patient_group", "family_id"} for row in train):
        raise IntakeError("Cần danh sách nhóm đầy đủ của dữ liệu huấn luyện.")
    return {(_safe_id(row["patient_group"]), _safe_id(row["family_id"])) for row in train}


def _split_counts(
    train_blob: bytes, validation: dict[str, Record], test: dict[str, Record]
) -> dict[str, Any]:
    """Reject split overlap and enforce evaluation size and calibration support."""
    groups = [
        {(record.patient_group, record.note.family_id) for record in split.values()}
        for split in (validation, test)
    ]
    check_groups([read_train_groups(train_blob), *groups])
    if validation.keys() & test.keys() or {item.note.text for item in validation.values()} & {
        item.note.text for item in test.values()
    }:
        raise IntakeError("Mã ghi chú hoặc văn bản trùng giữa validation và test.")
    support = Counter(item.label for record in test.values() for item in record.note.entities)
    if len(test) < 150 or sum(support.values()) < 800 or not set(GOLD_LABELS) <= support.keys():
        raise IntakeError("Test cần ≥150 ghi chú, ≥800 vùng vàng và đủ năm nhãn.")
    slices = Counter(name for record in test.values() for name in record.slices)
    if not SLICES.keys() <= slices.keys():
        raise IntakeError("Test thiếu lát cắt áp lực đã đăng ký trước.")
    slice_support = {
        name: dict(
            Counter(
                item.label
                for record in test.values()
                if name in record.slices
                for item in record.note.entities
            )
        )
        for name in SLICES
    }
    calibration: Counter[str] = Counter()
    families_by_label: defaultdict[str, set[str]] = defaultdict(set)
    for record in validation.values():
        for item in record.note.entities:
            calibration[item.label] += 1
            families_by_label[item.label].add(record.note.family_id)
    if any(calibration[label] < 100 or len(families_by_label[label]) < 3 for label in GOLD_LABELS):
        raise IntakeError("Validation cần ≥100 vùng và ≥3 họ mẫu cho từng nhãn.")
    return {
        "test_notes": len(test),
        "test_gold_by_label": dict(support),
        "test_slices": dict(slices),
        "test_slice_note_gold_by_label": slice_support,
        "validation_notes": len(validation),
        "validation_gold_by_label": dict(calibration),
        "validation_families_by_label": {k: len(v) for k, v in families_by_label.items()},
    }


def _iaa(payload: dict[str, bytes], test: dict[str, Record], sample: set[str]) -> dict[str, Any]:
    """Compute strict dual annotation agreement and verify every disagreement was adjudicated."""
    a, b, adjudicated = (_annotation(payload[name], name, test) for name in FILES[4:7])
    if a.keys() != sample or b.keys() != sample or len(sample) * 5 < len(test):
        raise IntakeError("Hai lượt phải gán đúng mẫu đã đăng ký, gồm ít nhất 20% ghi chú.")
    disagreements = {key for key in a if a[key].entities != b[key].entities}
    if disagreements != adjudicated.keys():
        raise IntakeError("Thiếu hoặc thừa bản phân xử cho tập bất đồng.")
    for key, either in a.items():
        if adjudicated.get(key, either).entities != test[key].note.entities:
            raise IntakeError("Nhãn vàng test khác kết quả đồng thuận hoặc phân xử.")
    metrics = score_documents(list(a.values()), {k: n.entities for k, n in b.items()}, 0)
    if metrics["micro"]["f1"] < 0.85:
        raise IntakeError("IAA strict entity-F1 dưới 0,85; chưa thể khóa tập.")
    return {
        "double_annotated_notes": len(a),
        "adjudicated_notes": len(disagreements),
        "strict_iaa": metrics["micro"],
        "strict_iaa_by_label": metrics["by_label"],
    }


def inspect_intake(directory: Path, protocol: Path = PROTOCOL) -> dict[str, Any]:
    """Validate the local bundle and return only hashes and aggregate counts for sealing."""
    from ml.phase_e_sampling import validate_sampling

    payload = {name: (directory / name).read_bytes() for name in FILES}
    provenance = _provenance(payload[FILES[0]])
    validation, test = (_records(payload[name], name) for name in FILES[2:4])
    counts = _split_counts(payload[FILES[1]], validation, test)
    reviewed = provenance["participant_reviewed_count"]
    if reviewed > len(test):
        raise IntakeError("Số ghi chú chủ dự án rà soát vượt kích thước tập test.")
    sample = validate_sampling(
        payload["source.jsonl"],
        payload["packet-manifest.json"],
        provenance["packet_manifest_sha256"],
        test,
    )
    return {
        "schema_version": 1,
        "source_type": provenance["source_type"],
        "participant_reviewed_count": reviewed,
        "preregistration_sha256": sha256(
            protocol.read_bytes().replace(b"\r\n", b"\n")
        ).hexdigest(),
        "files_sha256": {name: sha256(blob).hexdigest() for name, blob in payload.items()},
        "counts": counts,
        "agreement": _iaa(payload, test, sample),
    }


def main() -> None:
    """Seal locally without overwriting or verify the complete manifest against current bytes."""
    parser = ArgumentParser(description="Kiểm tra hồ sơ đánh giá độc lập của Phase E.")
    parser.add_argument("mode", choices=("check", "seal", "verify"))
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    try:
        manifest = inspect_intake(args.directory)
        path = args.directory / MANIFEST_NAME
        if args.mode == "seal":
            with path.open("x", encoding="utf-8", newline="\n") as output:
                json.dump(manifest, output, indent=2, sort_keys=True)
                output.write("\n")
        elif args.mode == "verify" and manifest != _read_payload(path.read_bytes(), MANIFEST_NAME):
            raise IntakeError("Manifest không khớp byte hoặc kết quả kiểm tra hiện tại.")
    except IntakeError as exc:
        parser.exit(1, f"Phase E: {exc}\n")
    except OSError:
        parser.exit(1, "Phase E: Thiếu tệp, thiếu quyền truy cập hoặc manifest đã tồn tại.\n")
    print(json.dumps(manifest, sort_keys=True))


if __name__ == "__main__":
    main()
