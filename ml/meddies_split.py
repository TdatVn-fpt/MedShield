# ml/meddies_split.py — Materialize only independently verified Meddies group assignments.
import json
from argparse import ArgumentParser
from collections.abc import Iterable
from hashlib import file_digest, sha256
from pathlib import Path
from typing import Any

from ml.meddies_qa import REVISION, SHARD_SHA256, cohort, text_hash, verified_rows
from ml.phase_e_intake import _read_payload, _safe_id
from ml.phase_e_preflight import audit_sources
from ml.phase_e_types import IntakeError

SPLITS = {"train", "validation", "test"}
ROW_FIELDS = {
    "note_id",
    "text_sha256",
    "patient_group",
    "family_id",
    "split",
    "slices",
    "evidence_ref",
}
LEDGER_FIELDS = {
    "schema_version",
    "revision",
    "shard_sha256",
    "evidence_sha256",
    "reviewer",
    "rows",
}


def _ledger(raw: bytes, evidence_sha256: str) -> dict[str, Any]:
    """Bind explicit assignments to a supplied source-evidence file and the pinned shard."""
    result = _read_payload(raw, "sổ nhóm Meddies")
    if (
        not isinstance(result, dict)
        or set(result) != LEDGER_FIELDS
        or type(result["schema_version"]) is not int
        or result["schema_version"] != 1
        or result["revision"] != REVISION
        or result["shard_sha256"] != SHARD_SHA256
        or result["evidence_sha256"] != evidence_sha256
        or not isinstance(result["rows"], list)
    ):
        raise IntakeError("Sổ nhóm không khớp bằng chứng hoặc shard đã đăng ký.")
    _safe_id(result["reviewer"])
    return result


def _assignments(ledger: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Require one explicit assignment and opaque evidence reference for every admitted note."""
    assignments = {}
    for row in ledger["rows"]:
        if not isinstance(row, dict) or set(row) != ROW_FIELDS:
            raise IntakeError("Một dòng sổ nhóm thiếu trường hoặc chứa dữ liệu ngoài hợp đồng.")
        note_id = _safe_id(row["note_id"])
        for key in ("patient_group", "family_id", "evidence_ref"):
            _safe_id(row[key])
        if (
            note_id in assignments
            or not isinstance(row["split"], str)
            or row["split"] not in SPLITS
        ):
            raise IntakeError("Mã ghi chú trùng hoặc phân tập không hợp lệ.")
        if row["split"] == "train" and row["slices"] != []:
            raise IntakeError("Không khai báo lát đánh giá cho ghi chú train.")
        assignments[note_id] = row
    return assignments


def _jsonl(rows: list[dict[str, Any]]) -> bytes:
    """Encode canonical UTF-8 LF files for Phase E tools."""
    return "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows).encode()


def prepare_split(
    rows: Iterable[dict[str, Any]], ledger_blob: bytes, evidence_sha256: str
) -> tuple[dict[str, bytes], dict[str, Any]]:
    """Verify group boundaries and render unlabelled sources and a train membership index."""
    assignments = _assignments(_ledger(ledger_blob, evidence_sha256))
    batches: dict[str, list[dict[str, Any]]] = {key: [] for key in sorted(SPLITS)}
    occupied: set[str] = set()
    found: set[str] = set()
    reserved: set[str] = set()
    seen_train: set[str] = set()
    admitted_train: set[str] = set()
    for row in rows:
        key = row["info"]["id"]
        candidate = cohort(row)
        if candidate not in {"provisional_train", "evaluation_candidate"}:
            if key in assignments:
                raise IntakeError("Sổ nhóm chứa ghi chú ngoài các nhóm nguồn đã duyệt.")
            continue
        fingerprint = text_hash(row["text"])
        if candidate == "evaluation_candidate":
            reserved.add(fingerprint)
        else:
            if fingerprint in seen_train and key in assignments:
                raise IntakeError("Sổ nhóm chứa bản trùng đã loại ở train tạm.")
            seen_train.add(fingerprint)
        if key not in assignments:
            continue
        plan = assignments[key]
        split = plan["split"]
        expected = "provisional_train" if split == "train" else "evaluation_candidate"
        if candidate != expected:
            raise IntakeError("Một ghi chú được gán vào tập ngoài nhóm nguồn đã dành.")
        if fingerprint != plan["text_sha256"]:
            raise IntakeError("SHA-256 văn bản không khớp dòng trong sổ nhóm.")
        if fingerprint in occupied or key in found:
            raise IntakeError("Ghi chú được nhận bị trùng mã hoặc nguyên văn.")
        occupied.add(fingerprint)
        if split == "train":
            admitted_train.add(fingerprint)
        found.add(key)
        group = {field: plan[field] for field in ("patient_group", "family_id")}
        entry = {"note_id": key, **group}
        if split != "train":
            entry.update(text=row["text"], source_group="meddies-clinical", slices=plan["slices"])
        batches[split].append(entry)
    if found != assignments.keys():
        raise IntakeError("Một số mã trong sổ nhóm không có trong shard đã ghim.")
    if admitted_train & reserved:
        raise IntakeError("Train trùng nguyên văn với nguồn đã dành cho đánh giá.")
    counts = {key: len(batch) for key, batch in batches.items()}
    if counts["train"] < 2000 or not 150 <= counts["test"] <= 200:
        raise IntakeError("Cần train ≥2.000 ghi chú đã xác minh và test từ 150 đến 200.")
    if counts["test"] + counts["validation"] < 200:
        raise IntakeError("Cần ít nhất 200 ứng viên đánh giá có bằng chứng nhóm.")
    for batch in batches.values():
        batch.sort(key=lambda item: item["note_id"])
    train_groups = sorted({(row["patient_group"], row["family_id"]) for row in batches["train"]})
    files = {
        "train-membership.jsonl": _jsonl(batches["train"]),
        "train-groups.jsonl": _jsonl(
            [{"patient_group": patient, "family_id": family} for patient, family in train_groups]
        ),
        "validation-source.jsonl": _jsonl(batches["validation"]),
        "source.jsonl": _jsonl(batches["test"]),
    }
    preflight = audit_sources(
        files["train-groups.jsonl"], files["validation-source.jsonl"], files["source.jsonl"]
    )
    return files, {
        "schema_version": 1,
        "status": "verified_ledger_pre_annotation_only",
        "revision": REVISION,
        "shard_sha256": SHARD_SHA256,
        "ledger_sha256": sha256(ledger_blob).hexdigest(),
        "evidence_sha256": evidence_sha256,
        "counts": counts,
        "preflight": preflight,
        "files_sha256": {name: sha256(contents).hexdigest() for name, contents in files.items()},
        "evaluation_labels_used": False,
        "locked": False,
    }


def main() -> None:
    """Run only inside the private workspace and emit no text or IDs to stdout."""
    parser = ArgumentParser(description="Chia tập Meddies bằng sổ nhóm đã xác minh.")
    for name in ("shard", "ledger", "evidence", "destination"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    local = (Path(__file__).resolve().parents[1] / "artifacts/local").resolve()
    inputs = [args.shard.resolve(), args.ledger.resolve(), args.evidence.resolve()]
    destination = args.destination.resolve()
    if any(not item.is_relative_to(local) for item in [*inputs, destination]):
        parser.error("Tất cả đường dẫn phải nằm trong artifacts/local.")
    try:
        with inputs[2].open("rb") as handle:
            if not handle.read(1):
                raise IntakeError("Tệp bằng chứng nhóm rỗng.")
            handle.seek(0)
            evidence_hash = file_digest(handle, "sha256").hexdigest()
        files, report = prepare_split(
            verified_rows(inputs[0]), inputs[1].read_bytes(), evidence_hash
        )
        destination.mkdir()
        for name, payload in files.items():
            (destination / name).write_bytes(payload)
        (destination / "meddies-split-manifest.json").write_bytes(
            (json.dumps(report, indent=2, ensure_ascii=False) + "\n").encode()
        )
    except IntakeError as exc:
        parser.exit(1, f"Meddies: {exc}\n")
    except (OSError, ValueError, KeyError):
        parser.exit(1, "Meddies: Tệp nguồn không đọc được hoặc không khớp manifest.\n")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
