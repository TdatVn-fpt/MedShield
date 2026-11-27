# ml/meddies_review_receipt.py — Bind the original Meddies review CSV to the sampled spans.
import csv
import json
from collections import Counter
from hashlib import sha256
from pathlib import Path
from typing import Any

from ml.bio import GOLD_LABELS
from ml.phase_e_types import IntakeError

HASH_FIELDS = ["sample_sha256", "label", "sample_index", "verdict", "reason"]
OWNER_FIELDS = ["label", "sample_no", "note_id", "value", "verdict", "reason"]


def mapping_review(samples: bytes, receipt: Path) -> dict[str, Any]:
    """Verify all 100 decisions against sample hashes or exact sample identities and values."""
    data = json.loads(samples)
    if (
        not isinstance(data, dict)
        or set(data) != set(GOLD_LABELS)
        or any(not isinstance(rows, list) or len(rows) != 20 for rows in data.values())
    ):
        raise IntakeError("Bộ mẫu ánh xạ phải có 20 vùng cho từng nhãn.")

    expected = {
        (label, str(index)): sample
        for label, rows in data.items()
        for index, sample in enumerate(rows, 1)
    }
    seen: set[tuple[str, str]] = set()
    digest = sha256(samples).hexdigest()
    corrections: Counter[str] = Counter()
    with receipt.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames not in (HASH_FIELDS, OWNER_FIELDS):
            raise IntakeError("Phiếu soát ánh xạ sai cột.")
        owner_format = reader.fieldnames == OWNER_FIELDS
        index_field = "sample_no" if owner_format else "sample_index"
        for row in reader:
            label, verdict = row["label"], row["verdict"]
            key = (label, row[index_field])
            if (
                key not in expected
                or key in seen
                or None in row
                or None in row.values()
                or verdict not in {"ok", "needs_correction"}
                or (verdict == "needs_correction" and not row["reason"].strip())
            ):
                raise IntakeError("Phiếu soát ánh xạ thiếu quyết định hoặc không khớp mẫu.")
            if owner_format:
                sample = expected[key]
                matches = isinstance(sample, dict) and all(
                    row[field] == sample.get(field) for field in ("note_id", "value")
                )
            else:
                matches = row["sample_sha256"] == digest
            if not matches:
                raise IntakeError("Phiếu soát ánh xạ không khớp giá trị mẫu gốc.")
            seen.add(key)
            corrections[label] += verdict == "needs_correction"
    if seen != expected.keys():
        raise IntakeError("Chủ dự án cần ghi đủ 100 quyết định soát mẫu ánh xạ.")
    return {
        "reviewed": len(seen),
        "corrections_by_label": dict(sorted(corrections.items())),
        "sample_sha256": digest,
        "owner_receipt_sha256": sha256(receipt.read_bytes()).hexdigest(),
    }
