# ml/meddies_silver.py — Validate blind human/LLM returns and record Meddies adjudication locally.
import json
from argparse import ArgumentParser
from collections import Counter
from hashlib import sha256
from pathlib import Path
from typing import Any

from ml.bio import GOLD_LABELS, Span
from ml.dataset import Note, parse_note
from ml.meddies_agreement import agreement_intervals, support_threshold
from ml.meddies_annotator import MODEL, PROMPT, REVISION, RUNTIME
from ml.meddies_dedup import LIMITATION
from ml.meddies_recovery import llm_receipts
from ml.meddies_review_receipt import mapping_review as mapping_review
from ml.meddies_split import _jsonl
from ml.phase_e_intake import _rows, _safe_id
from ml.phase_e_types import IntakeError
from ml.scoring import score_documents

SPLITS = ("validation", "test")


def packet_rows(blob: bytes) -> dict[str, str]:
    """Read exactly the original blind note IDs and Unicode text."""
    notes: dict[str, str] = {}
    for row in _rows(blob, "gói gán mù"):
        key = _safe_id(row.get("note_id"))
        if set(row) != {"note_id", "text"} or not isinstance(row["text"], str) or key in notes:
            raise IntakeError("Gói gán mù sai trường hoặc trùng mã.")
        notes[key] = row["text"]
    if not notes:
        raise IntakeError("Gói gán mù rỗng.")
    return notes


def parse_returns(blob: bytes, texts: dict[str, str]) -> dict[str, Note]:
    """Require complete annotations with valid nonoverlapping spans for the supplied texts."""
    notes = {}
    for row in _rows(blob, "nhãn trả về"):
        key = _safe_id(row.get("note_id"))
        if key in notes or key not in texts or set(row) != {"note_id", "entities"}:
            raise IntakeError("Nhãn chứa mã trùng, thừa trường hoặc ghi chú ngoài gói.")
        if not isinstance(row["entities"], list) or any(
            not isinstance(span, dict) or set(span) != {"label", "start", "end"}
            for span in row["entities"]
        ):
            raise IntakeError("Mỗi vùng nhãn chỉ gồm start, end và label.")
        try:
            # Required by the shared parser. This marker is never written out as a group.
            notes[key] = parse_note(dict(row, text=texts[key], family_id="unverified"))
        except (ValueError, TypeError):
            raise IntakeError("Biên hoặc nhãn không hợp lệ trên văn bản nguyên gốc.") from None
    if notes.keys() != texts.keys():
        raise IntakeError("Thiếu ghi chú trả về, kể cả ghi chú không có vùng.")
    return notes


def _regions(spans: tuple[Span, ...]) -> list[dict[str, Any]]:
    """Encode sorted spans without entity surfaces."""
    return [{"start": s.start, "end": s.end, "label": s.label} for s in spans]


def compare(a: dict[str, Note], b: dict[str, Note]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Use the frozen strict scorer before any human adjudication."""
    differences = [
        {
            "note_id": key,
            "text": a[key].text,
            "entities_a": _regions(a[key].entities),
            "entities_b": _regions(b[key].entities),
        }
        for key in sorted(a)
        if a[key].entities != b[key].entities
    ]
    score = score_documents(
        [a[key] for key in sorted(a)], {key: list(b[key].entities) for key in b}, example_limit=0
    )
    return differences, {
        "iaa_type": "human_llm",
        "double_annotated": len(a),
        "disagreements": len(differences),
        "disagreement_rate": len(differences) / len(a) if a else 0.0,
        "strict_micro": score["micro"],
        "strict_by_label": score["by_label"],
        "iaa_threshold_met": score["micro"]["f1"] >= 0.85,
        "confidence_interval_95": agreement_intervals(a, b),
    }


def write_adjudication_packets(
    directory: Path, split: str, disputes: list[dict[str, Any]]
) -> None:
    """Prepare exact-text disputes and two unconfirmed drafts for the offline editor."""
    (directory / f"{split}-disputes.jsonl").write_bytes(_jsonl(disputes))
    if not disputes:
        return
    packet = _jsonl([{"note_id": row["note_id"], "text": row["text"]} for row in disputes])
    (directory / f"{split}-adjudication-packet.jsonl").write_bytes(packet)
    digest = sha256(packet).hexdigest()
    for annotator in ("a", "b"):
        draft = {
            "schema_version": 1,
            "packet_sha256": digest,
            "rows": [
                {
                    "note_id": row["note_id"],
                    "reviewed": False,
                    "entities": row[f"entities_{annotator}"],
                }
                for row in disputes
            ],
        }
        (directory / f"{split}-adjudication-draft-{annotator}.json").write_text(
            json.dumps(draft, ensure_ascii=False), encoding="utf-8"
        )


def _run_split(
    packets: Path,
    results: Path,
    destination: Path,
    manifest: dict[str, Any],
    split: str,
    guideline: bytes,
) -> dict[str, Any]:
    """Bind both returns to the preregistered packet and expose all discrepancies to the owner."""
    name = f"{split}-blind.jsonl"
    packet = (packets / name).read_bytes()
    fingerprint = sha256(packet).hexdigest()
    texts = packet_rows(packet)
    if (
        fingerprint != manifest["packet_sha256"][name]
        or len(texts) != manifest["split_counts"][split]
    ):
        raise IntakeError("Gói gán mù khác manifest chia tập.")
    a_file = (results / f"{split}-a.jsonl").read_bytes()
    b_files = results / f"{split}-qwen"
    b_file = (b_files / "annotations-b.jsonl").read_bytes()
    prompt = PROMPT.encode() + guideline
    receipt, completion = llm_receipts(b_files, b_file, len(texts), prompt.decode("utf-8"), texts)
    b_meta = json.loads(receipt)
    if (
        b_meta.get("model") != MODEL
        or b_meta.get("model_revision") != REVISION
        or b_meta.get("runtime") != RUNTIME
        or b_meta.get("packet_sha256") != fingerprint
        or b_meta.get("guideline_sha256") != sha256(guideline).hexdigest()
        or b_meta.get("prompt_sha256") != sha256(prompt).hexdigest()
    ):
        raise IntakeError("Lượt LLM sai mô hình, gói hoặc hướng dẫn đã chốt.")
    a, b = parse_returns(a_file, texts), parse_returns(b_file, texts)
    disputes, report = compare(a, b)
    report["iaa_gate_applies"] = split == "test"
    for annotator, notes in (("a", a), ("b", b)):
        counts = Counter(span.label for note in notes.values() for span in note.entities)
        label_counts = {label: counts[label] for label in sorted(GOLD_LABELS)}
        report[f"provisional_support_{annotator}"] = {
            "notes": len(notes),
            "total": counts.total(),
            "by_label": label_counts,
            "threshold_met": support_threshold(split, len(notes), label_counts),
        }
    disputed = {row["note_id"]: row["text"] for row in disputes}
    write_adjudication_packets(destination, split, disputes)
    report["input_sha256"] = {
        "packet": fingerprint,
        "a": sha256(a_file).hexdigest(),
        "b": sha256(b_file).hexdigest(),
        "b_receipt": sha256(receipt).hexdigest(),
        "b_completion": sha256(completion).hexdigest(),
    }
    decisions = results / f"{split}-adjudication.jsonl"
    if not decisions.is_file():
        return report
    decided = parse_returns(decisions.read_bytes(), disputed)
    if split == "test" and not report["iaa_threshold_met"]:
        return report
    resolved = {**a, **decided}
    labels = Counter(span.label for note in resolved.values() for span in note.entities)
    report["resolved_support"] = {label: labels[label] for label in sorted(GOLD_LABELS)}
    report["adjudication_sha256"] = sha256(decisions.read_bytes()).hexdigest()
    report["support_threshold_met"] = support_threshold(
        split, len(resolved), report["resolved_support"]
    )
    if report["support_threshold_met"]:
        data = _jsonl(
            [
                {"note_id": key, "text": note.text, "entities": _regions(note.entities)}
                for key, note in sorted(resolved.items())
            ]
        )
        (destination / f"{split}-resolved.jsonl").write_bytes(data)
        report["resolved_sha256"] = sha256(data).hexdigest()
    return report


def main() -> None:
    """Build a private review, keeping final authorization and training outside this command."""
    parser = ArgumentParser(description="Đo IAA người–LLM và chuẩn bị phân xử Meddies.")
    for field in ("packets", "results", "manifest", "destination"):
        parser.add_argument(field, type=Path)
    parser.add_argument("--mapping-samples", type=Path)
    parser.add_argument("--mapping-review", type=Path)
    root = Path(__file__).resolve().parents[1]
    parser.add_argument("--guideline", type=Path, default=root / "docs/annotation-guide.md")
    args = parser.parse_args()
    local = (Path(__file__).resolve().parents[1] / "artifacts/local").resolve()
    if not all(
        path.resolve().is_relative_to(local)
        for path in (args.packets, args.results, args.destination)
    ):
        parser.error("Gói, nhãn và kết quả riêng phải nằm trong artifacts/local.")
    mapping_paths = (args.mapping_samples, args.mapping_review)
    if any(mapping_paths) and not all(
        path is not None and path.resolve().is_relative_to(local) for path in mapping_paths
    ):
        parser.error("Cần cả hai tệp soát ánh xạ trong artifacts/local.")
    try:
        manifest = json.loads(args.manifest.read_bytes())
        guideline = args.guideline.read_bytes()
        args.destination.mkdir()
        report = {
            split: _run_split(
                args.packets, args.results, args.destination, manifest, split, guideline
            )
            for split in SPLITS
        }
        result = {
            "evaluation_label_tier_target": "silver-locked",
            "limitation": LIMITATION,
            "locked": False,
            "splits": report,
        }
        if args.mapping_samples and args.mapping_review:
            result["mapping_review"] = mapping_review(
                args.mapping_samples.read_bytes(), args.mapping_review
            )
        (args.destination / "review.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    except IntakeError as exc:
        parser.exit(1, f"Meddies: {exc}\n")
    except (OSError, ValueError, KeyError, TypeError):
        parser.exit(1, "Meddies: Thiếu tệp trả về hoặc tệp không khớp giao thức.\n")


if __name__ == "__main__":
    main()
