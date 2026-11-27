# ml/meddies_qa.py — Audit the pinned Vietnamese Meddies shard and reserve evaluation candidates.
import json
from argparse import ArgumentParser
from collections import Counter
from collections.abc import Iterator
from hashlib import file_digest, sha256
from pathlib import Path
from typing import Any

REVISION = "5dbe7cde649446028f628820c204bf53bb296894"
SHARD_SHA256 = "331640296be10a56a468e1cf9d5014dc9d1de13ab304b9294df0643b2ddbc04a"
TRAIN_SOURCE = "Meddies/mimo-meddies9-targeted-synthetic"
EVAL_SOURCE = "Meddies/local-new-data-clinical-synthetic"
TRAIN_TYPES = frozenset(
    {
        "pharmacy refill request",
        "discharge summary",
        "lab result notification",
        "insurance claim note",
        "patient portal access log",
        "telehealth triage note",
        "referral letter",
        "outpatient note",
        "medical bill / invoice",
        "appointment reminder",
        "HL7-style admission/update message",
        "FHIR-like Patient + Encounter resource",
        "ambient voice scribe transcript",
        "OCR-scanned clinical note",
    }
)
EVAL_TYPES = frozenset(
    {
        "TRANSFER_FORM",
        "LAB_RESULT",
        "SURGERY_SCHEDULE",
        "DISCHARGE_SUMMARY",
        "OUTPATIENT_EXAMINATION",
        "IMAGING_REPORT",
        "MEDICAL_BILL",
        "REFERRAL_LETTER",
        "MORTALITY_REPORT",
        "PRESCRIPTION",
        "MEDICATION_CHART",
        "IMMUNIZATION_RECORD",
        "PHYSICAL_THERAPY_PLAN",
        "NURSING_NOTE",
        "MEDICAL_RECORD",
        "CONSENT_FORM",
    }
)
LINEAGE_FIELDS = ("original_id", "scenario", "domain_profile", "source", "source_dataset")


def verified_rows(shard: Path, annotations: bool = False) -> Iterator[dict[str, Any]]:
    """Read the exact locally approved shard with optional labels for the training stage only."""
    import pyarrow.parquet as parquet

    with shard.open("rb") as handle:
        if file_digest(handle, "sha256").hexdigest() != SHARD_SHA256:
            raise ValueError("SHA-256 shard Meddies không khớp bản đã kiểm.")
    columns = ["text", "info", "label"] if annotations else ["text", "info"]
    for batch in parquet.ParquetFile(shard).iter_batches(columns=columns):
        yield from batch.to_pylist()


def cohort(row: dict[str, Any]) -> str:
    """Use approved medical metadata and an explicit document-type list to admit candidates."""
    info, text = row["info"], row["text"]
    if not isinstance(text, str) or not text.strip() or len(text) > 50_000:
        return "text_unusable"
    if (
        info["language_bucket"] != "vi"
        or info["domain_bucket"] != "medical"
        or info["domain_profile"] != "medical"
    ):
        return "not_medical_vi"
    source, kind = info["source_dataset"], info["document_type"]
    if source == EVAL_SOURCE and kind in EVAL_TYPES:
        return "evaluation_candidate"
    if source == TRAIN_SOURCE and kind in TRAIN_TYPES and info["split_purpose"] == "train":
        return "provisional_train"
    return "medical_metadata_insufficient"


def text_hash(text: str) -> str:
    """Fingerprint verbatim original text to catch exact duplicates, including across cohorts."""
    return sha256(text.encode("utf-8")).hexdigest()


def _lineage(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize declared lineage without exposing values or treating them as patient IDs."""
    report = {}
    for field in LINEAGE_FIELDS:
        known = Counter(row["info"][field] for row in rows if row["info"].get(field))
        report[field] = {
            "present": sum(known.values()),
            "distinct": len(known),
            "repeated_values": sum(count > 1 for count in known.values()),
            "verified_patient_or_family_key": False,
        }
    return report


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Return reproducible code-point lengths, document types and coverage for candidates."""
    lengths = sorted(len(row["text"]) for row in rows)
    return {
        "count": len(rows),
        "length_code_points": {
            name: lengths[int((len(lengths) - 1) * q)] if lengths else None
            for name, q in {"min": 0, "p50": 0.5, "p95": 0.95, "max": 1}.items()
        },
        "document_types": dict(
            sorted(Counter(row["info"]["document_type"] for row in rows).items())
        ),
        "lineage": _lineage(rows),
    }


def audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Count admitted rows and exclude duplicate texts before checking the numeric Step 1 gate."""
    by_type: dict[str, list[dict[str, Any]]] = {
        "provisional_train": [],
        "evaluation_candidate": [],
    }
    totals: Counter[str] = Counter()
    for row in rows:
        group = cohort(row)
        totals[group] += 1
        if group in by_type:
            by_type[group].append(row)
    reserved = {text_hash(row["text"]) for row in by_type["evaluation_candidate"]}
    exclusions: Counter[str] = Counter()
    for group, entries in by_type.items():
        seen = set(reserved) if group == "provisional_train" else set()
        kept = []
        for row in entries:
            digest = text_hash(row["text"])
            if digest in seen:
                exclusions[group] += 1
            else:
                seen.add(digest)
                kept.append(row)
        by_type[group] = kept
    return {
        "revision": REVISION,
        "license": "CC-BY-NC-4.0",
        "shard_sha256": SHARD_SHA256,
        "total_rows": len(rows),
        "raw_cohort_counts": dict(totals),
        "exact_text_exclusions": dict(exclusions),
        "cohorts": {group: _summary(entries) for group, entries in by_type.items()},
        "numeric_gate_met": len(by_type["provisional_train"]) >= 2000
        and len(by_type["evaluation_candidate"]) >= 200,
        "patient_and_family_disjointness_verified": False,
        "status": "candidate_counts_only",
    }


def main() -> None:
    """Write an aggregate QA manifest with no note text, labels, or source IDs."""
    parser = ArgumentParser(description="Kiểm QA shard Meddies tiếng Việt đã ghim.")
    parser.add_argument("shard", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(list(verified_rows(args.shard)))
    with args.output.open("x", encoding="utf-8", newline="\n") as output:
        output.write(json.dumps(result, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
