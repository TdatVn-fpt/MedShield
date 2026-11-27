# ml/meddies_lock.py — Seal and verify Meddies silver evidence before any training or selection.
import json
from argparse import ArgumentParser
from collections import Counter
from hashlib import sha256
from pathlib import Path
from typing import Any

from ml.bio import GOLD_LABELS
from ml.meddies_annotator import MODEL, PROMPT, RUNTIME
from ml.meddies_annotator import REVISION as LLM_REVISION
from ml.meddies_dedup import LIMITATION
from ml.meddies_qa import REVISION, SHARD_SHA256
from ml.meddies_recovery import llm_receipts
from ml.meddies_silver import (
    SPLITS,
    compare,
    mapping_review,
    packet_rows,
    parse_returns,
)
from ml.meddies_slices import support
from ml.meddies_split import _jsonl
from ml.phase_e_intake import _rows
from ml.phase_e_types import IntakeError

SCORER = "6f3f4e8b4c242c6f418003cb192a1dba967ad3161b0957a89adc9c3e5ab512c0"
SOURCE_MANIFEST = "7a9d584b0ccca862f72f0467d44ad88d1f551bcf932e34bac67b6fc2e9e505e7"
MAPPING_MANIFEST = "945d803961dccc7a9932a662ded1a12ce0accf9ba29230820a67424b19da0ed4"
LOCK_NAME = "meddies-silver-lock.json"
GATES = {
    "strict_micro_f1": 0.88,
    "recall_min_by_label": {"ADDR": 0.90, "DOB": 0.90, "ID": 0.95, "NAME": 0.90, "PHONE": 0.95},
    "note_leak_rate_max": 0.05,
    "strict_addr_f1": 0.80,
}


def _load(path: Path) -> tuple[bytes, dict[str, Any]]:
    """Return input bytes and its JSON object for signing and validation."""
    blob = path.read_bytes()
    result = json.loads(blob)
    if not isinstance(result, dict):
        raise IntakeError("Tệp bằng chứng yêu cầu đối tượng JSON.")
    return blob, result


def _attestation(result: dict[str, Any]) -> None:
    """Require explicit owner confirmation of blind review and any mapping corrections."""
    if (
        not isinstance(result.get("owner"), str)
        or not result["owner"].strip()
        or result.get("human_annotation_complete") is not True
        or result.get("adjudication_complete") is not True
        or result.get("mapping_review_complete") is not True
        or result.get("mapping_corrections_resolved") is not True
        or type(result.get("revision_round")) is not int
        or not 0 <= result["revision_round"] <= 2
    ):
        raise IntakeError("Thiếu xác nhận của chủ dự án cho gán mù, phân xử hoặc phiếu soát mẫu.")


def _check_split(
    split: str,
    packets: Path,
    evidence: Path,
    manifest: dict[str, Any],
    guideline_sha: str,
    prompt_sha: str,
    primary_prompt: str | None = None,
) -> dict[str, Any]:
    """Recompute IAA and resolved support directly from independent returns and owner decisions."""
    filename = f"{split}-blind.jsonl"
    source = (packets / filename).read_bytes()
    digest = sha256(source).hexdigest()
    texts = packet_rows(source)
    if (
        digest != manifest["packet_sha256"][filename]
        or len(texts) != manifest["split_counts"][split]
    ):
        raise IntakeError("Gói gán mù khác bản chốt trước gán.")
    a_path = evidence / f"{split}-a.jsonl"
    b_path = evidence / f"{split}-qwen/annotations-b.jsonl"
    adjudicated_path = evidence / f"{split}-adjudication.jsonl"
    a_blob, b_blob = a_path.read_bytes(), b_path.read_bytes()
    raw_receipt, completion = llm_receipts(
        b_path.parent, b_blob, len(texts), primary_prompt, texts
    )
    receipt = json.loads(raw_receipt)
    if (
        receipt.get("model") != MODEL
        or receipt.get("model_revision") != LLM_REVISION
        or receipt.get("runtime") != RUNTIME
        or receipt.get("packet_sha256") != digest
        or receipt.get("guideline_sha256") != guideline_sha
        or receipt.get("prompt_sha256") != prompt_sha
    ):
        raise IntakeError("Lượt LLM sai mô hình, gói hoặc hướng dẫn đã chốt.")
    a, b = parse_returns(a_blob, texts), parse_returns(b_blob, texts)
    disputes, iaa = compare(a, b)
    if split == "test" and not iaa["iaa_threshold_met"]:
        raise IntakeError(f"IAA strict người–LLM dưới 0,85 ở {split}.")
    adjudicated_blob = adjudicated_path.read_bytes()
    chosen = parse_returns(adjudicated_blob, {row["note_id"]: row["text"] for row in disputes})
    resolved_blob = (evidence / f"{split}-resolved.jsonl").read_bytes()
    resolved_rows = []
    for row in _rows(resolved_blob, "bản sau phân xử"):
        if set(row) != {"note_id", "text", "entities"}:
            raise IntakeError("Bản sau phân xử sai trường.")
        if texts.get(row["note_id"]) != row.pop("text"):
            raise IntakeError("Văn bản sau phân xử khác gói gán mù.")
        resolved_rows.append(row)
    resolved = parse_returns(_jsonl(resolved_rows), texts)
    if resolved != {**a, **chosen}:
        raise IntakeError("Bản sau phân xử khác quyết định của chủ dự án.")
    counts = Counter(span.label for note in resolved.values() for span in note.entities)
    if split == "test" and (not 150 <= len(resolved) <= 200 or counts.total() < 800):
        raise IntakeError("Test chưa đủ 150–200 ghi chú và ít nhất 800 vùng.")
    minimum = 100 if split == "validation" else 1
    if any(counts[label] < minimum for label in GOLD_LABELS):
        raise IntakeError(f"Support từng nhãn của {split} chưa đạt ngưỡng.")
    return {
        **iaa,
        "participant_reviewed_count": len(a),
        "support": dict(sorted(counts.items())),
        "slice_support": support(resolved.values()),
        "sha256": {
            "packet": digest,
            "human": sha256(a_blob).hexdigest(),
            "llm": sha256(b_blob).hexdigest(),
            "llm_receipt": sha256(raw_receipt).hexdigest(),
            "llm_completion": sha256(completion).hexdigest(),
            "adjudication": sha256(adjudicated_blob).hexdigest(),
            "resolved": sha256(resolved_blob).hexdigest(),
        },
    }


def inspect(
    packets: Path, evidence: Path, source_manifest: Path, samples_path: Path, guideline: Path
) -> dict[str, Any]:
    """Verify source, human evidence, IAA and support and assemble the locked manifest."""
    source_bytes, source = _load(source_manifest)
    if (
        sha256(source_bytes).hexdigest() != SOURCE_MANIFEST
        or source.get("status") != "awaiting_blind_annotation"
        or source.get("revision") != REVISION
        or source.get("shard_sha256") != SHARD_SHA256
        or source.get("limitation") != LIMITATION
        or source.get("source_overlap_count") != 0
        or source.get("evaluation_publisher_labels_used") is not False
    ):
        raise IntakeError("Manifest nguồn chưa đạt điều kiện Meddies.")
    owner_bytes, owner = _load(evidence / "owner-attestation.json")
    _attestation(owner)
    root = Path(__file__).resolve().parents[1]
    if sha256((root / "ml/scoring.py").read_bytes()).hexdigest() != SCORER:
        raise IntakeError("Scorer không khớp SHA-256 đã đóng băng.")
    guide = guideline.read_bytes()
    guideline_sha = sha256(guide).hexdigest()
    prompt_sha = sha256(PROMPT.encode() + guide).hexdigest()
    primary_prompt = PROMPT + guide.decode("utf-8")
    if owner.get("guideline_sha256") != guideline_sha:
        raise IntakeError("Xác nhận của người gán thiếu SHA-256 đúng của hướng dẫn.")
    mapper_blob, mapper = _load(root / "artifacts/meddies-step2-mapping.json")
    sample_bytes = samples_path.read_bytes()
    if (
        sha256(mapper_blob).hexdigest() != MAPPING_MANIFEST
        or mapper.get("training_pool_sha256") != source.get("mapped_train_sha256")
        or mapper.get("review_samples_sha256") != sha256(sample_bytes).hexdigest()
    ):
        raise IntakeError("Mẫu soát không thuộc chính bản ánh xạ train đã dùng để khử trùng.")
    dependencies = ("ml/meddies_slices.py", "ml/evaluation_slices.py", "uv.lock")
    return {
        "schema_version": 1,
        "locked": True,
        "evaluation_label_tier": "silver-locked",
        "iaa_type": "human_llm",
        "source": source,
        "source_manifest_sha256": sha256(source_bytes).hexdigest(),
        "limitation": LIMITATION,
        "annotator_a": owner["owner"],
        "adjudicator": owner["owner"],
        "annotator_b": {"model": MODEL, "revision": LLM_REVISION},
        "revision_round": owner["revision_round"],
        "owner_attestation_sha256": sha256(owner_bytes).hexdigest(),
        "guideline_sha256": guideline_sha,
        "scorer_sha256": SCORER,
        "slice_dependencies_sha256": {
            item: sha256((root / item).read_bytes()).hexdigest() for item in dependencies
        },
        "step2_manifest_sha256": sha256(mapper_blob).hexdigest(),
        "mapping_review": mapping_review(sample_bytes, evidence / "mapping-review.csv"),
        "phase_m_gates": GATES,
        "splits": {
            split: _check_split(
                split, packets, evidence, source, guideline_sha, prompt_sha, primary_prompt
            )
            for split in SPLITS
        },
    }


def main() -> None:
    """Seal once or verify the exact locked contents, without printing data or annotator IDs."""
    parser = ArgumentParser(description="Khóa hoặc xác minh tập Meddies silver-locked cục bộ.")
    parser.add_argument("action", choices=("seal", "verify"))
    for field in ("packets", "evidence", "source_manifest", "samples", "guideline"):
        parser.add_argument(field, type=Path)
    args = parser.parse_args()
    local = (Path(__file__).resolve().parents[1] / "artifacts/local").resolve()
    if not all(
        p.resolve().is_relative_to(local) for p in (args.packets, args.evidence, args.samples)
    ):
        parser.error("Gói, bằng chứng và mẫu phải nằm trong artifacts/local.")
    try:
        path = args.evidence / LOCK_NAME
        report = inspect(
            args.packets, args.evidence, args.source_manifest, args.samples, args.guideline
        )
        payload = (
            json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        ).encode()
        if args.action == "seal":
            with path.open("xb") as handle:
                handle.write(payload)
        elif path.read_bytes() != payload:
            raise IntakeError("Bằng chứng hiện tại khác manifest silver-locked.")
        print(f"Meddies {args.action}: {sha256(payload).hexdigest()}")
    except IntakeError as exc:
        parser.exit(1, f"Meddies: {exc}\n")
    except (OSError, ValueError, KeyError, TypeError):
        parser.exit(1, "Meddies: Thiếu tệp khóa hoặc bằng chứng không hợp lệ.\n")


if __name__ == "__main__":
    main()
