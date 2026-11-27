# tests/test_meddies_m_preflight_data.py — Check train-only partitioning and Unicode BIO edges.
import json
from collections import Counter
from pathlib import Path

import pytest

from ml.bio import Span
from ml.meddies_m_preflight_data import _prepared_note, _rank_rows, load_pilot_data
from ml.meddies_m_segment import BOUNDARY, _aligned_words, _segmented_rows


def test_train_partition_is_stable_and_disjoint() -> None:
    """Reordering JSONL records cannot move an ID between the same seeded partitions."""
    rows = [json.dumps({"note_id": f"train-{index}"}).encode() for index in range(40)]
    train, validation = _rank_rows(b"\n".join(rows) + b"\n", seed=17)
    assert train and validation
    assert not set(train) & set(validation)
    assert set(train) | set(validation) == set(rows)
    assert _rank_rows(b"\n".join(reversed(rows)), seed=17) == (train, validation)
    with pytest.raises(ValueError, match="trùng"):
        _rank_rows(b"\n".join([*rows, rows[0]]), seed=17)


def test_train_alignment_keeps_original_text_and_combining_code_points() -> None:
    """Trim whitespace in the training view and keep decomposed characters intact."""
    raw = {
        "note_id": "train-1",
        "text": "🙂\tÁn\r\nBình",
        "entities": [{"start": 1, "end": 7, "label": "NAME"}],
    }
    trimmed: Counter[str] = Counter()
    note = _prepared_note(raw, trimmed)
    assert note.text == raw["text"]
    assert note.entities == (Span(2, 5, "NAME"),)
    assert raw["entities"] == [{"start": 1, "end": 7, "label": "NAME"}]
    assert trimmed == {"NAME": 1}


def test_pilot_rejects_a_self_declared_manifest_before_reading_pool(tmp_path: Path) -> None:
    """Only the QA-approved report can authorize reading a local candidate train pool."""
    candidate = Path("artifacts/local/meddies/never-read/provisional-train.jsonl")
    fake_manifest = tmp_path / "mapping.json"
    fake_manifest.write_text('{"status":"provisional_train_remapped_after_owner_review"}')
    with pytest.raises(ValueError, match="bản train đã qua QA"):
        load_pilot_data(candidate, fake_manifest, 1, 1, 17)


def test_vietnamese_segmenter_preserves_original_code_point_ranges() -> None:
    """Map joined words and alternate accent placement over untouched source text."""
    text = "🙂 Án\r\nToà nhà"
    words = _aligned_words(text, ["🙂", "Án", "Tòa_nhà"])
    assert words is not None
    assert [text[word.source.start : word.source.end] for word in words] == [
        "🙂",
        "Án",
        "Toà nhà",
    ]
    assert _aligned_words(text, ["🙂", "Tòa_nhà"]) is None
    assert _aligned_words("ß", ["s", "s"]) is None
    assert _aligned_words("Mai \u0301 An", ["Mai", "An"]) is None
    spaced = _aligned_words("Mai\u202fAn", ["Mai\u202fAn", "\u202f"])
    assert spaced is not None and spaced[0].value == "Mai_An"
    assert (spaced[0].source.start, spaced[0].source.end) == (0, 6)


def test_segmentation_rows_require_exact_batch_boundaries() -> None:
    """Accept token IDs wrapping per sentence and require each requested note in the batch."""
    output = f"1\tĐoạn_một\t_\n\n1\t{BOUNDARY}\t_\n\n1\tĐoạn_hai\t_"
    assert _segmented_rows(output, 2) == [["Đoạn_một"], ["Đoạn_hai"]]
    with pytest.raises(ValueError, match="khác số"):
        _segmented_rows(output, 3)
