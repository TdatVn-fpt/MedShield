# ml/phase_e_preflight.py — Audit source splits before sending blind annotation packets.
import json
from argparse import ArgumentParser
from collections import Counter
from hashlib import sha256
from pathlib import Path
from typing import Any

from ml.phase_e_annotation import SourceNote, read_source
from ml.phase_e_groups import check_groups
from ml.phase_e_intake import read_train_groups
from ml.phase_e_types import SLICES, IntakeError


def _counts(split: dict[str, SourceNote]) -> dict[str, Any]:
    """Summarize declared source coverage using only public slice names and aggregate counts."""
    slices = Counter(key for item in split.values() for key in item.slices)
    return {
        "notes": len(split),
        "patient_groups": len({item.patient_group for item in split.values()}),
        "families": len({item.note.family_id for item in split.values()}),
        "declared_slice_notes": {key: slices[key] for key in SLICES},
    }


def audit_sources(train_blob: bytes, validation_blob: bytes, test_blob: bytes) -> dict[str, Any]:
    """Validate reported grouping and preliminary viable sizes without reading any gold labels."""
    train = read_train_groups(train_blob)
    validation, test = read_source(validation_blob), read_source(test_blob)
    groups = [
        {(item.patient_group, item.note.family_id) for item in split.values()}
        for split in (validation, test)
    ]
    check_groups([train, *groups])
    if validation.keys() & test.keys() or {v.note.text for v in validation.values()} & {
        v.note.text for v in test.values()
    }:
        raise IntakeError("Mã ghi chú hoặc văn bản trùng giữa validation và test.")
    validation_counts, test_counts = _counts(validation), _counts(test)
    if validation_counts["families"] < 3:
        raise IntakeError("Validation chưa có ít nhất 3 họ nguồn cần để hiệu chuẩn.")
    if len(test) < 150 or not all(test_counts["declared_slice_notes"].values()):
        raise IntakeError("Test trước gán cần ít nhất 150 ghi chú và đủ các lát đã đăng ký.")
    return {
        "schema_version": 1,
        "stage": "before_annotation",
        "input_sha256": {
            "train_groups": sha256(train_blob).hexdigest(),
            "validation_source": sha256(validation_blob).hexdigest(),
            "test_source": sha256(test_blob).hexdigest(),
        },
        "train_group_pairs": len(train),
        "validation": validation_counts,
        "test": test_counts,
    }


def main() -> None:
    """Print aggregate checks without creating files or logging note texts and group IDs."""
    parser = ArgumentParser(description="Kiểm tra tách nguồn Phase E trước khi gán nhãn.")
    for argument in ("train_groups", "validation_source", "test_source"):
        parser.add_argument(argument, type=Path)
    args = parser.parse_args()
    try:
        result = audit_sources(
            args.train_groups.read_bytes(),
            args.validation_source.read_bytes(),
            args.test_source.read_bytes(),
        )
    except IntakeError as exc:
        parser.exit(1, f"Phase E: {exc}\n")
    except OSError:
        parser.exit(1, "Phase E: Không đọc được một trong các tệp nguồn.\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
