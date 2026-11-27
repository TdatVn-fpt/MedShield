# ml/meddies_dedup.py — Audit authorized Meddies source isolation and emit local blind packets.
import json
from argparse import ArgumentParser
from collections import Counter, defaultdict
from fractions import Fraction
from hashlib import sha256
from pathlib import Path
from typing import Any

from ml.meddies_overlap import Shingle, SurfaceIndex, max_similarity, shingles, surface_keys, words
from ml.meddies_qa import (
    EVAL_SOURCE,
    REVISION,
    SHARD_SHA256,
    TRAIN_SOURCE,
    _summary,
    cohort,
    text_hash,
    verified_rows,
)
from ml.meddies_split import _jsonl
from ml.phase_e_types import IntakeError

LIMITATION = (
    "tách tập bằng cô lập nguồn sinh + khử trùng trùng lặp gần giống; "
    "phân nhóm bệnh nhân/họ mẫu không kiểm chứng được từ metadata công khai của nhà phát hành"
)
SEED = 20261126
TEST_COUNT = 150


def _cohorts(shard: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build Step 1 source cohorts and reserve evaluation text before deduplicating train."""
    pools: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in verified_rows(shard):
        pools[cohort(row)].append(row)
    train, evaluation = pools["provisional_train"], pools["evaluation_candidate"]
    source_train = {row["info"]["source"] for row in train}
    source_eval = {row["info"]["source"] for row in evaluation}
    if len(source_train) != 13 or len(source_eval) != 1 or source_train & source_eval:
        raise IntakeError("Nguồn sinh không khớp cô lập nguồn đã duyệt.")
    reserved = {text_hash(row["text"]) for row in evaluation}
    return _unique(train, reserved), _unique(evaluation, set())


def _unique(rows: list[dict[str, Any]], seen: set[str]) -> list[dict[str, Any]]:
    """Keep the first occurrence of each exact document, excluding pre-reserved text."""
    result = []
    for row in rows:
        digest = text_hash(row["text"])
        if digest not in seen:
            result.append(row)
            seen.add(digest)
    return result


def _train_surfaces(mapping: Path, expected: dict[str, str]) -> tuple[SurfaceIndex, str]:
    """Check the mapped train file against all admitted text and build entity surface keys."""
    index, digest, seen = SurfaceIndex(), sha256(), set()
    with mapping.open("rb") as stream:
        for line in stream:
            digest.update(line)
            row = json.loads(line)
            key, text = row["note_id"], row["text"]
            if key in seen or expected.get(key) != text_hash(text):
                raise IntakeError("Tệp ánh xạ không khớp ghi chú train đã duyệt.")
            seen.add(key)
            names: set[Shingle] = set()
            values: set[tuple[str, Shingle]] = set()
            for span in row["entities"]:
                label = span["label"]
                value = text[span["start"] : span["end"]]
                if label == "NAME":
                    name = tuple(words(value))
                    if name:
                        names.add(name)
                elif label in {"PHONE", "DOB"}:
                    values.update((label, token) for token in surface_keys(value, label))
            index.add(names, values)
    if seen != expected.keys():
        raise IntakeError("Tệp ánh xạ thiếu ghi chú train đã duyệt.")
    return index, digest.hexdigest()


def _distribution(scores: list[Fraction]) -> dict[str, Any]:
    """Report exact bin counts and floor-index quantiles without per-note information."""
    counts = [sum(Fraction(i, 10) < s <= Fraction(i + 1, 10) for s in scores) for i in range(10)]
    ordered = sorted(scores)
    return {
        "zero": scores.count(Fraction(0)),
        "intervals_open_left_closed_right": {
            f"({i / 10:.1f}, {(i + 1) / 10:.1f}]": count for i, count in enumerate(counts)
        },
        **{
            name: float(ordered[int((len(ordered) - 1) * q)])
            for name, q in {"min": 0, "p50": 0.5, "p95": 0.95, "max": 1}.items()
        },
    }


def audit(shard: Path, mapping: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Compare fresh evaluation notes with the entire eligible train pool before splitting."""
    train, evaluation = _cohorts(shard)
    expected = {row["info"]["id"]: text_hash(row["text"]) for row in train}
    if len(expected) != len(train) or len(train) < 2000 or not evaluation:
        raise IntakeError("Không xác nhận được danh sách train hoặc ứng viên đánh giá.")
    index, mapped_sha = _train_surfaces(mapping, expected)
    grams = [shingles(words(row["text"]), 5) for row in evaluation]
    scores = max_similarity(grams, (row["text"] for row in train))
    kept, counts = [], Counter[str]()
    for row, score in zip(evaluation, scores, strict=True):
        labels = {match[0] for match in index.matches(row["text"])}
        near = score > Fraction(1, 2)
        counts["near"] += near
        counts["surface"] += bool(labels)
        counts["both"] += near and bool(labels)
        counts["name_phone"] += "PHONE" in labels
        counts["name_dob"] += "DOB" in labels
        if not near and not labels:
            kept.append(row)
    return kept, {
        "schema_version": 1,
        "revision": REVISION,
        "license": "CC-BY-NC-4.0",
        "shard_sha256": SHARD_SHA256,
        "mapped_train_sha256": mapped_sha,
        "train_source_dataset": TRAIN_SOURCE,
        "evaluation_source_dataset": EVAL_SOURCE,
        "train_source_count": 13,
        "evaluation_source_count": 1,
        "source_overlap_count": 0,
        "train": _summary(train),
        "evaluation_before": _summary(evaluation),
        "evaluation_after": _summary(kept),
        "similarity": {
            "method": "exact_word_5gram_set_jaccard_nfc_casefold",
            "threshold_exclusive": 0.5,
            "pairs_examined": len(train) * len(evaluation),
            "candidate_max_distribution": _distribution(scores),
        },
        "exclusions": {**dict(counts), "total": len(evaluation) - len(kept)},
        "surface_rule": "train_mapped_name_phone_or_dob_pair_in_unlabelled_candidate_text",
        "limitation": LIMITATION,
        "patient_and_family_disjointness_verified": False,
        "evaluation_publisher_labels_used": False,
        "evaluation_label_tier_target": "silver-locked",
        "iaa_type": "human_llm",
        "locked": False,
    }


def _packet(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Emit only text and opaque identifiers, in a deterministic data-independent order."""
    items = [
        {"note_id": "meddies-" + text_hash(row["text"])[:24], "text": row["text"]} for row in rows
    ]
    return sorted(items, key=lambda item: item["note_id"])


def blind_split(rows: list[dict[str, Any]]) -> tuple[dict[str, bytes], dict[str, Any]]:
    """Allocate 150 test records proportionally by document type and maximize validation size."""
    if len(rows) < 200:
        raise IntakeError("Không đủ ứng viên để giữ 150 test và ít nhất 200 ghi chú đánh giá.")
    buckets: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[row["info"]["document_type"]].append(row)
    quotas = {
        kind: Fraction(len(batch) * TEST_COUNT, len(rows)) for kind, batch in buckets.items()
    }
    allocations = {kind: int(quota) for kind, quota in quotas.items()}
    remainder = TEST_COUNT - sum(allocations.values())
    for kind in sorted(quotas, key=lambda k: (allocations[k] - quotas[k], k))[:remainder]:
        allocations[kind] += 1
    test, validation = [], []
    for kind, batch in buckets.items():
        ordered = sorted(batch, key=lambda row: text_hash(f"{SEED}:{row['text']}"))
        test.extend(ordered[: allocations[kind]])
        validation.extend(ordered[allocations[kind] :])
    cross_scores = max_similarity(
        [shingles(words(row["text"]), 5) for row in test],
        (row["text"] for row in validation),
    )
    if any(score > Fraction(1, 2) for score in cross_scores):
        raise IntakeError("Có trùng gần giống qua biên validation/test.")
    files = {
        "test-blind.jsonl": _jsonl(_packet(test)),
        "validation-blind.jsonl": _jsonl(_packet(validation)),
    }
    return files, {
        "validation": _summary(validation),
        "test": _summary(test),
        "test_max_jaccard_against_validation": float(max(cross_scores)),
    }


def main() -> None:
    """Write a sanitized aggregate and separate local blind packets when thresholds allow."""
    parser = ArgumentParser(description="Khử trùng và chia gói gán mù Meddies theo nguồn.")
    for name in ("shard", "mapping", "destination", "report"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    local = (Path(__file__).resolve().parents[1] / "artifacts/local").resolve()
    if any(
        not path.resolve().is_relative_to(local)
        for path in (args.shard, args.mapping, args.destination)
    ):
        parser.error("Shard, ánh xạ và gói gán mù phải nằm trong artifacts/local.")
    if args.destination.exists() or args.report.exists():
        parser.error("Đường dẫn đầu ra phải mới.")
    try:
        kept, report = audit(args.shard, args.mapping)
        report["status"] = (
            "below_owner_floor_150" if len(kept) < 150 else "below_existing_minimum_evaluation"
        )
        if len(kept) >= 200:
            files, split_report = blind_split(kept)
            args.destination.mkdir()
            for name, data in files.items():
                (args.destination / name).write_bytes(data)
            report.update(
                status="awaiting_blind_annotation",
                split_seed=SEED,
                split_counts={"test": TEST_COUNT, "validation": len(kept) - TEST_COUNT},
                split_audit=split_report,
                packet_sha256={name: sha256(data).hexdigest() for name, data in files.items()},
            )
        with args.report.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    except IntakeError as exc:
        parser.exit(1, f"Meddies: {exc}\n")
    except (OSError, ValueError, KeyError, TypeError):
        parser.exit(1, "Meddies: Tệp nguồn hoặc đầu ra không đọc được.\n")


if __name__ == "__main__":
    main()
