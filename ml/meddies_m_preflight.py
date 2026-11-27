# ml/meddies_m_preflight.py — Fine-tune the pinned pilot only on train-side data.
import json
from argparse import ArgumentParser, Namespace
from collections import Counter
from dataclasses import replace
from hashlib import file_digest
from importlib import import_module
from itertools import islice
from math import isfinite
from os import cpu_count, environ
from pathlib import Path
from platform import platform, processor
from random import Random
from time import perf_counter
from typing import Any

from ml.bio import Span
from ml.dataset import Note
from ml.meddies_agreement import agreement_intervals
from ml.meddies_m_features import (
    BIO_TAGS,
    IGNORE_INDEX,
    FeatureWindow,
    WordFeatures,
    build_features,
    decode_word_tags,
    merge_window_tags,
)
from ml.meddies_m_preflight_data import PREFLIGHT_SEED, load_pilot_data
from ml.meddies_m_segment import SegmentedWord, segment_notes
from ml.scoring import score_documents

CHECKPOINT = "demdecuong/vihealthbert-base-word"
CHECKPOINT_REVISION = "f89e80b461e86f9cfc1c84019bd819830c24b6c5"
WEIGHT_SHA256 = "3259d96cb56cb1c85b0a5a894e782a6a4ee66d783333d83368fba36d23be2d06"
CHECKPOINT_FILES = ["config.json", "bpe.codes", "vocab.txt", "pytorch_model.bin"]


def _checkpoint(cache: Path, transformers: Any) -> tuple[Any, Any]:
    """Download only the pinned base and load verified weights with local model code."""
    hub = import_module("huggingface_hub")
    path = Path(
        hub.snapshot_download(
            CHECKPOINT,
            revision=CHECKPOINT_REVISION,
            allow_patterns=CHECKPOINT_FILES,
            cache_dir=cache,
        )
    )
    with (path / "pytorch_model.bin").open("rb") as weights:
        if file_digest(weights, "sha256").hexdigest() != WEIGHT_SHA256:
            raise ValueError("Trọng số ViHealthBERT không khớp SHA-256 của checkpoint đã ghim.")
    tokenizer = transformers.PhobertTokenizer.from_pretrained(path, local_files_only=True)
    names = dict(enumerate(BIO_TAGS))
    model = transformers.AutoModelForTokenClassification.from_pretrained(
        path,
        local_files_only=True,
        trust_remote_code=False,
        weights_only=True,
        num_labels=len(names),
        id2label=names,
        label2id={name: index for index, name in names.items()},
    )
    return model, tokenizer


def _position_features(
    notes: list[Note], segmenter: Path, tokenizer: Any
) -> tuple[dict[str, tuple[list[SegmentedWord], WordFeatures]], dict[str, Any]]:
    """Build model windows and record all gold spans that cannot feed training loss."""
    rows = segment_notes([note.text for note in notes], segmenter)
    features = {}
    ignored: Counter[str] = Counter()
    invalid = windows = oversize = 0
    for note, words in zip(notes, rows, strict=True):
        if not words:
            invalid += 1
            ignored.update(span.label for span in note.entities)
            continue
        accepted = build_features(note, words, tokenizer)
        features[note.note_id] = (words, accepted)
        ignored.update(accepted.excluded_support)
        windows += len(accepted.windows)
        oversize += accepted.oversize_words
    return features, {
        "notes_without_aligned_words": invalid,
        "windows": windows,
        "oversize_words": oversize,
        "excluded_gold_by_label": dict(sorted(ignored.items())),
    }


def _batch(windows: list[FeatureWindow], pad: int, torch: Any) -> dict[str, Any]:
    """Return CPU tensors padded only to the longest window in the batch."""
    width = max(len(window.input_ids) for window in windows)
    rows, masks, tags = [], [], []
    for window in windows:
        size = len(window.input_ids)
        missing = width - size
        rows.append([*window.input_ids, *([pad] * missing)])
        masks.append([1] * size + [0] * missing)
        tags.append([*window.labels, *([IGNORE_INDEX] * missing)])
    return {
        "input_ids": torch.tensor(rows, dtype=torch.long),
        "attention_mask": torch.tensor(masks, dtype=torch.long),
        "labels": torch.tensor(tags, dtype=torch.long),
    }


def _train(
    model: Any, windows: list[FeatureWindow], pad: int, args: Namespace, torch: Any
) -> dict[str, Any]:
    """Update pretrained parameters over a deterministic CPU sample and record elapsed time."""
    if not windows:
        raise ValueError("Không có cửa sổ train nào có nhãn hợp lệ.")
    chosen = islice(windows, args.steps * args.batch_size)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate)
    model.train()
    losses = []
    start = perf_counter()
    for _ in range(args.steps):
        batch = list(islice(chosen, args.batch_size))
        if not batch:
            break
        optimizer.zero_grad(set_to_none=True)
        loss = model(**_batch(batch, pad, torch)).loss
        value = float(loss.detach().item())
        if not isfinite(value):
            raise ValueError("Giá trị loss chạy thử không hữu hạn.")
        loss.backward()
        optimizer.step()
        losses.append(value)
    return {"seconds": perf_counter() - start, "updates": len(losses), "losses": losses}


def _predict(
    model: Any,
    notes: list[Note],
    features: dict[str, tuple[list[SegmentedWord], WordFeatures]],
    pad: int,
    torch: Any,
) -> dict[str, list[Span]]:
    """Decode each word once and keep all internal validation notes in the denominator."""
    model.eval()
    predictions: dict[str, list[Span]] = {note.note_id: [] for note in notes}
    with torch.inference_mode():
        for note_id, (words, prepared) in features.items():
            window_tags = []
            for window in prepared.windows:
                inputs = _batch([window], pad, torch)
                del inputs["labels"]
                window_tags.append(model(**inputs).logits[0].argmax(dim=-1).tolist())
            word_tags = merge_window_tags(prepared.windows, window_tags, len(words))
            predictions[note_id] = decode_word_tags(words, word_tags)
    return predictions


def run_pilot(args: Namespace, work: Path) -> dict[str, Any]:
    """Train a short CPU pilot and build a metadata-only result with its exact inputs."""
    environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    torch = import_module("torch")
    transformers = import_module("transformers")
    torch.set_num_threads(args.threads)
    torch.manual_seed(args.seed)
    data = load_pilot_data(
        args.pool, args.manifest, args.train_notes, args.validation_notes, args.seed
    )
    load_start = perf_counter()
    model, tokenizer = _checkpoint(work / "checkpoint-cache", transformers)
    load_seconds = perf_counter() - load_start
    prep_start = perf_counter()
    train, train_summary = _position_features(data.train, args.segmenter, tokenizer)
    validation, validation_summary = _position_features(data.validation, args.segmenter, tokenizer)
    prep_seconds = perf_counter() - prep_start
    eligible = [
        window
        for _, prepared in train.values()
        for window in prepared.windows
        if any(tag != IGNORE_INDEX for tag in window.labels)
    ]
    Random(args.seed).shuffle(eligible)
    training = _train(model, eligible, tokenizer.pad_token_id, args, torch)
    eval_start = perf_counter()
    predictions = _predict(model, data.validation, validation, tokenizer.pad_token_id, torch)
    score = score_documents(data.validation, predictions, example_limit=0)
    reference = {note.note_id: note for note in data.validation}
    predicted = {
        key: replace(note, entities=tuple(predictions[key])) for key, note in reference.items()
    }
    intervals = agreement_intervals(reference, predicted)
    eval_seconds = perf_counter() - eval_start
    return {
        **data.metadata,
        "checkpoint": {
            "repo": CHECKPOINT,
            "revision": CHECKPOINT_REVISION,
            "sha256": WEIGHT_SHA256,
        },
        "software": {"torch": torch.__version__, "transformers": transformers.__version__},
        "hardware": {
            "platform": platform(),
            "processor": processor(),
            "logical_cpus": cpu_count(),
            "device": "cpu",
            "torch_threads": torch.get_num_threads(),
        },
        "config": {
            "optimizer": "AdamW",
            "learning_rate": args.learning_rate,
            "batch_size": args.batch_size,
            "requested_steps": args.steps,
            "window_tokens": 256,
            "overlap_tokens_requested": 48,
        },
        "train_features": train_summary,
        "validation_features": validation_summary,
        "training": training,
        "timing_seconds": {
            "checkpoint_load": load_seconds,
            "feature_preparation": prep_seconds,
            "internal_validation_scoring": eval_seconds,
        },
        "internal_validation_strict": score,
        "internal_validation_strict_f1_ci95": intervals["strict_f1"],
        "bootstrap_draws": intervals["draws"],
        "bootstrap_seed": intervals["seed"],
    }


def main() -> None:
    """Run the pilot only with a verified train pool and write a new local result."""
    parser = ArgumentParser(
        description="Chạy thử ViHealthBERT bản word chỉ trên phía train Meddies."
    )
    for field in ("pool", "manifest", "segmenter", "output"):
        parser.add_argument(field, type=Path)
    parser.add_argument("--seed", type=int, default=PREFLIGHT_SEED)
    parser.add_argument("--train-notes", type=int, default=64)
    parser.add_argument("--validation-notes", type=int, default=24)
    parser.add_argument("--steps", type=int, default=16)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--threads", type=int, default=6)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    args = parser.parse_args()
    work = (
        Path(__file__).resolve().parents[1] / "artifacts/local/meddies/phase-m-preflight"
    ).resolve()
    if (
        not args.output.resolve().is_relative_to(work)
        or args.output.exists()
        or not args.output.parent.is_dir()
        or not args.segmenter.resolve().is_relative_to(work)
        or min(args.threads, args.steps, args.batch_size) < 1
        or not isfinite(args.learning_rate)
        or args.learning_rate <= 0
    ):
        parser.error(
            "Bộ tách từ và kết quả mới phải ở thư mục chạy thử cục bộ, với tham số hợp lệ."
        )
    result = run_pilot(args, work)
    with args.output.open("x", encoding="utf-8", newline="\n") as output:
        output.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print("Đã lưu kết quả validation nội bộ phía train, không dùng tuyên bố.")


if __name__ == "__main__":
    main()
