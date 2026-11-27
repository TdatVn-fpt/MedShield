# ml/phase_e_evaluate.py — Score frozen model predictions against a sealed Phase E bundle.
import json
from argparse import ArgumentParser
from collections.abc import Callable, Mapping, Sequence
from hashlib import sha256
from pathlib import Path
from typing import Any

from ml.bio import GOLD_LABELS, Span
from ml.dataset import parse_note
from ml.evaluation_metrics import BOOTSTRAP_SEED, MIN_DRAWS, counts, note_has_leak, summarize
from ml.evaluation_slices import SLICE_LABELS, classify_span
from ml.phase_e_intake import (
    MANIFEST_NAME,
    SLICES,
    IntakeError,
    Record,
    _read_payload,
    _records,
    inspect_intake,
)
from ml.scoring import score_documents

SCORER_SHA256 = "6f3f4e8b4c242c6f418003cb192a1dba967ad3161b0957a89adc9c3e5ab512c0"
METHOD_MODES = {"rules": "rules", "crf": "ner", "transformer": "ner", "hybrid": "hybrid"}
PROVENANCE_HASHES = (
    "candidate_revision_sha256",
    "selection_evidence_sha256",
    "inference_evidence_sha256",
)
STRUCTURE_SLICES = {
    name: label for name, label in SLICE_LABELS.items() if label in {"PHONE", "ADDR"}
}


def _digest(value: object) -> bool:
    """Recognize a lowercase SHA-256 identifier without accepting unchecked free text."""
    return isinstance(value, str) and len(value) == 64 and set(value) <= set("0123456789abcdef")


def _object(items: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject ambiguous duplicate keys in the prediction envelope and every nested record."""
    result = dict(items)
    if len(result) != len(items):
        raise IntakeError("Tệp dự đoán chứa trường JSON trùng.")
    return result


def _sealed_bundle(directory: Path) -> tuple[dict[str, Any], str, dict[str, Record]]:
    """Revalidate the sealed intake and bind in-memory test bytes to the verified manifest."""
    manifest = inspect_intake(directory)
    sealed = (directory / MANIFEST_NAME).read_bytes()
    if manifest != _read_payload(sealed, MANIFEST_NAME):
        raise IntakeError("Manifest Phase E đã khóa không khớp với bundle đang chấm.")
    test = (directory / "test.jsonl").read_bytes()
    if sha256(test).hexdigest() != manifest["files_sha256"]["test.jsonl"]:
        raise IntakeError("Tệp test thay đổi sau khi kiểm tra manifest.")
    return manifest, sha256(sealed).hexdigest(), _records(test, "test.jsonl")


def parse_predictions(
    blob: bytes,
    expected_sha256: str,
    manifest: Mapping[str, Any],
    seal_sha256: str,
    records: Mapping[str, Record],
) -> tuple[dict[str, tuple[Span, ...]], dict[str, Any]]:
    """Load sealed, observed model spans covering every test note and return safe identity."""
    digest = sha256(blob).hexdigest()
    if not _digest(expected_sha256) or digest != expected_sha256:
        raise IntakeError("SHA-256 tệp dự đoán không khớp giá trị đóng băng do QA cung cấp.")
    try:
        envelope = json.loads(blob.decode("utf-8"), object_pairs_hook=_object)
    except (ValueError, UnicodeError):
        raise IntakeError("Tệp dự đoán không phải JSON UTF-8 hợp lệ.") from None
    fields = {
        "schema_version",
        "test_sha256",
        "manifest_sha256",
        "selection_validation_sha256",
        "selected_before_test",
        "observed_inference",
        "method",
        "mode",
        "model_checkpoint_sha256",
        "predictions",
        *PROVENANCE_HASHES,
    }
    if (
        not isinstance(envelope, dict)
        or set(envelope) != fields
        or type(envelope["schema_version"]) is not int
        or envelope["schema_version"] != 1
        or not all(_digest(envelope[field]) for field in PROVENANCE_HASHES)
        or envelope["selected_before_test"] is not True
        or envelope["observed_inference"] is not True
    ):
        raise IntakeError("Thiếu bằng chứng lựa chọn trước test hoặc lượt suy luận thực tế.")
    test_hashes = manifest["files_sha256"]
    if (
        envelope["test_sha256"] != test_hashes["test.jsonl"]
        or envelope["manifest_sha256"] != seal_sha256
        or envelope["selection_validation_sha256"] != test_hashes["validation.jsonl"]
    ):
        raise IntakeError("Tệp dự đoán không thuộc test, validation và manifest đã khóa này.")
    method, mode = envelope["method"], envelope["mode"]
    model_hash = envelope["model_checkpoint_sha256"]
    if not isinstance(method, str) or method not in METHOD_MODES or mode != METHOD_MODES[method]:
        raise IntakeError("Phương pháp và chế độ engine không tương ứng.")
    if (method == "rules" and model_hash is not None) or (
        method != "rules" and not _digest(model_hash)
    ):
        raise IntakeError("SHA-256 checkpoint không phù hợp với phương pháp.")
    items = envelope["predictions"]
    if not isinstance(items, list) or len(items) != len(records):
        raise IntakeError("Dự đoán phải có đúng một bản ghi cho mỗi ghi chú test.")
    predictions: dict[str, tuple[Span, ...]] = {}
    for item in items:
        if not isinstance(item, dict) or set(item) != {"note_id", "entities"}:
            raise IntakeError("Bản ghi dự đoán chỉ gồm mã ghi chú và các vùng máy đề xuất.")
        key, entities = item["note_id"], item["entities"]
        if not isinstance(key, str) or key not in records or key in predictions:
            raise IntakeError("Dự đoán bị trùng hoặc chứa mã ghi chú ngoài test.")
        if not isinstance(entities, list) or any(
            not isinstance(span, dict) or set(span) != {"start", "end", "label"}
            for span in entities
        ):
            raise IntakeError("Vùng dự đoán chỉ gồm start, end và label.")
        note = records[key].note
        try:
            parsed = parse_note({**item, "family_id": note.family_id, "text": note.text})
        except (ValueError, TypeError):
            raise IntakeError("Biên hoặc nhãn vùng dự đoán không hợp lệ.") from None
        predictions[key] = parsed.entities
    public = {key: envelope[key] for key in fields - {"predictions", "schema_version"}}
    return predictions, {**public, "prediction_sha256": digest}


def gate_gaps(overall: Mapping[str, Any], by_label: Mapping[str, Any]) -> dict[str, Any]:
    """Report preregistered M threshold inequalities and their nonnegative absolute gaps."""
    strict = [("strict_micro_f1", overall["strict"]["f1"], 0.88)]
    strict += [
        (f"strict_recall_{label}", by_label[label]["strict"]["recall"], floor)
        for label, floor in {
            "NAME": 0.90,
            "DOB": 0.90,
            "ADDR": 0.90,
            "PHONE": 0.95,
            "ID": 0.95,
        }.items()
    ]
    strict.append(("strict_addr_f1", by_label["ADDR"]["strict"]["f1"], 0.80))
    leak = overall["document_leak_rate"]
    rows = [
        {"criterion": name, "value": actual, "minimum": floor, "gap": max(0.0, floor - actual)}
        for name, actual, floor in strict
    ]
    rows.append(
        {
            "criterion": "document_leak_rate",
            "value": leak,
            "maximum": 0.05,
            "gap": max(0.0, leak - 0.05),
        }
    )
    return {
        "basis": "point_estimate",
        "all_thresholds_met": all(row["gap"] == 0 for row in rows),
        "criteria": rows,
    }


def _group(
    records: Sequence[Record],
    predictions: Mapping[str, Sequence[Span]],
    draws: int,
    include: Callable[[Record, Span], bool],
    skip_empty: bool = False,
) -> dict[str, Any]:
    """Measure scoped entities and actual uncovered gold using all available mask spans."""
    rows, leaks = [], []
    for record in records:
        note = record.note
        masks = set(predictions[note.note_id])
        gold = {span for span in note.entities if include(record, span)}
        selected = {span for span in masks if include(record, span)}
        if skip_empty and not gold and not selected:
            continue
        rows.append(counts(gold, selected))
        leaks.append(note_has_leak(note.text, gold, masks))
    return summarize(rows, leaks, draws, BOOTSTRAP_SEED)


def _label_scope(label: str | None) -> Callable[[Record, Span], bool]:
    """Create an entity membership predicate for a single label or all labels."""
    return lambda _record, span: label is None or span.label == label


def _structure_scope(key: str) -> Callable[[Record, Span], bool]:
    """Partition spans by fixed PHONE structure or by the ADDR residence cue."""
    return lambda record, span: classify_span(record.note, span) == key


def evaluate(
    records: Sequence[Record], predictions: Mapping[str, Sequence[Span]], draws: int
) -> dict[str, Any]:
    """Compute aggregate diagnostics only, preserving the frozen scorer for primary claims."""
    strict = score_documents([record.note for record in records], predictions, example_limit=0)
    overall = _group(records, predictions, draws, _label_scope(None))
    by_label = {
        label: _group(records, predictions, draws, _label_scope(label)) for label in GOLD_LABELS
    }
    if overall["strict"] != strict["micro"] or any(
        summary["strict"] != strict["by_label"][label] for label, summary in by_label.items()
    ):
        raise IntakeError("Số đếm bootstrap không khớp scorer strict đã đóng băng.")
    return {
        "overall": {**overall, "strict": strict["micro"]},
        "strict_notes_with_fn": strict["notes_with_fn"],
        "strict_document_fn_rate": strict["notes_with_fn"] / len(records),
        "by_label": {
            label: {**summary, "strict": strict["by_label"][label]}
            for label, summary in by_label.items()
        },
        "declared_note_slices": {
            name: {
                "target_label": label,
                **_group(
                    [record for record in records if name in record.slices],
                    predictions,
                    draws,
                    _label_scope(label),
                ),
            }
            for name, label in SLICES.items()
        },
        "structure_span_slices": {
            name: _group(records, predictions, draws, _structure_scope(name), skip_empty=True)
            for name in STRUCTURE_SLICES
        },
        "phase_m_thresholds": gate_gaps(overall, by_label),
    }


def main() -> None:
    """Verify all bindings, then create a private aggregate report without overwriting it."""
    parser = ArgumentParser(description="Chấm dự đoán đã khóa trên test độc lập Phase E.")
    parser.add_argument("directory", type=Path)
    parser.add_argument("predictions", type=Path)
    parser.add_argument("--prediction-sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--draws", type=int, default=MIN_DRAWS)
    args = parser.parse_args()
    if args.draws < MIN_DRAWS:
        parser.error("--draws phải từ 1000 trở lên.")
    try:
        scorer = Path(__file__).with_name("scoring.py").read_bytes().replace(b"\r\n", b"\n")
        if sha256(scorer).hexdigest() != SCORER_SHA256:
            raise IntakeError("Scorer strict không khớp SHA-256 đã đóng băng.")
        manifest, digest, records = _sealed_bundle(args.directory)
        predictions, identity = parse_predictions(
            args.predictions.read_bytes(), args.prediction_sha256, manifest, digest, records
        )
        metrics = evaluate(list(records.values()), predictions, args.draws)
        aggregate = {
            "schema_version": 1,
            "source_type": manifest["source_type"],
            "preregistration_sha256": manifest["preregistration_sha256"],
            "scorer_sha256": SCORER_SHA256,
            "identity": identity,
            "bootstrap": {
                "unit": "note",
                "draws": args.draws,
                "seed": BOOTSTRAP_SEED,
                "confidence": 0.95,
            },
            "partial": "exact_boundary_1_nonempty_overlap_0.5_ignores_label_within_scope",
            "leak": "unmasked_non_whitespace_gold_code_point",
            "review_required": True,
            **metrics,
        }
        with args.output.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(aggregate, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
    except IntakeError as exc:
        parser.exit(1, f"Phase E: {exc}\n")
    except (OSError, ValueError, TypeError, KeyError):
        parser.exit(1, "Phase E: Tệp không khả dụng, không hợp lệ hoặc đầu ra đã tồn tại.\n")


if __name__ == "__main__":
    main()
