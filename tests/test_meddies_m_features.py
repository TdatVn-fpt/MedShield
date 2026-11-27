# tests/test_meddies_m_features.py — Check BIO ownership and Unicode using a local BPE fixture.
import re

import pytest

from ml.bio import GOLD_LABELS, Span
from ml.dataset import Note
from ml.meddies_m_features import (
    IGNORE_INDEX,
    TAG_IDS,
    build_features,
    decode_word_tags,
    merge_window_tags,
)
from ml.meddies_m_segment import SegmentedWord
from ml.tokenization import Token


class ToyBpe:
    """Simulate whitespace BPE with stable piece IDs and explicit boundary tokens."""

    unk_token_id = 3

    def encode(self, text: str, *, add_special_tokens: bool) -> list[int]:
        """Encode slash-separated fixture pieces without implicit special IDs."""
        assert not add_special_tokens
        return [10 + (sum(map(ord, part)) % 300) for part in text.split("/")]

    def build_inputs_with_special_tokens(self, token_ids_0: list[int]) -> list[int]:
        """Wrap encoded fixture words in one leading and one trailing position."""
        return [0, *token_ids_0, 2]

    def get_special_tokens_mask(self, token_ids_0: list[int]) -> list[int]:
        """Mark only inserted positions, even if a payload value equals a special ID."""
        return [1, *([0] * len(token_ids_0)), 1]


def _word(text: str, original: str, encoded: str | None = None) -> SegmentedWord:
    """Make an explicitly aligned segmented word from an invented original substring."""
    start = text.index(original)
    return SegmentedWord(encoded or original, Token(start, start + len(original)))


def _words(text: str) -> list[SegmentedWord]:
    """Make one source word per whitespace-separated fixture token."""
    return [SegmentedWord(match[0], Token(*match.span())) for match in re.finditer(r"\S+", text)]


def _span(word: SegmentedWord, label: str) -> Span:
    """Return a gold interval exactly covering a single segmented word."""
    return Span(word.source.start, word.source.end, label)


def test_five_labels_and_first_piece_on_original_code_points() -> None:
    """Preserve all labels, a leading emoji, and a combining mark under grouped word BPE."""
    text = "🙂 Lê Thảo 1987 0900000000 BN-001 Phố Hoa"
    words = [
        _word(text, "🙂"),
        _word(text, "Lê Thảo", "Lê_/Thảo"),
        _word(text, "1987"),
        _word(text, "0900000000", "09/00000000"),
        _word(text, "BN-001"),
        _word(text, "Phố Hoa", "Phố_Hoa"),
    ]
    gold = tuple(_span(word, label) for word, label in zip(words[1:], GOLD_LABELS, strict=True))
    features = build_features(Note("n1", "fixture", text, gold), words, ToyBpe())
    (window,) = features.windows
    assert window.owned_positions == ((1, 0), (2, 1), (4, 2), (5, 3), (7, 4), (8, 5))
    assert window.labels == (
        IGNORE_INDEX,
        TAG_IDS["O"],
        TAG_IDS["B-NAME"],
        IGNORE_INDEX,
        TAG_IDS["B-DOB"],
        TAG_IDS["B-PHONE"],
        IGNORE_INDEX,
        TAG_IDS["B-ID"],
        TAG_IDS["B-ADDR"],
        IGNORE_INDEX,
    )
    assert features.excluded_support == dict.fromkeys(GOLD_LABELS, 0)
    assert decode_word_tags(
        words, merge_window_tags(features.windows, [window.labels], 6)
    ) == list(gold)


def test_partial_overlap_masks_touched_words_and_keeps_gold_for_scoring() -> None:
    """Ignore training labels across a cut word without altering the strict scoring spans."""
    text = "🙂 Lê Thảo An 2000"
    words = [_word(text, part) for part in ("🙂", "Lê Thảo", "An", "2000")]
    words[1] = _word(text, "Lê Thảo", "Lê_Thảo")
    name = Span(text.index("Thảo"), words[2].source.end, "NAME")
    gold = (name, _span(words[3], "DOB"))
    note = Note("n2", "fixture", text, gold)
    features = build_features(note, words, ToyBpe())
    (window,) = features.windows
    assert [window.labels[index] for index, _ in window.owned_positions] == [
        TAG_IDS["O"],
        IGNORE_INDEX,
        IGNORE_INDEX,
        TAG_IDS["B-DOB"],
    ]
    assert features.excluded_support == {**dict.fromkeys(GOLD_LABELS, 0), "NAME": 1}
    assert note.entities is gold


def test_window_ownership_is_central_and_decodes_across_windows() -> None:
    """Assign each word once, favor earlier ties, and join entities across window boundaries."""
    text = " ".join(f"w{index}" for index in range(12))
    words = _words(text)
    gold = (Span(words[4].source.start, words[8].source.end, "ADDR"),)
    features = build_features(
        Note("n3", "fixture", text, gold), words, ToyBpe(), max_length=8, overlap_tokens=3
    )
    assert [len(window.input_ids) for window in features.windows] == [8, 8, 8]
    assert [[word for _, word in window.owned_positions] for window in features.windows] == [
        [0, 1, 2, 3, 4],
        [5, 6, 7],
        [8, 9, 10, 11],
    ]
    predictions = []
    for window in features.windows:
        predicted = [TAG_IDS["B-ID"]] * (len(window.input_ids) + 1)
        for position, _ in window.owned_positions:
            predicted[position] = window.labels[position]
        predictions.append(predicted)
    assert decode_word_tags(
        words, merge_window_tags(features.windows, predictions, len(words))
    ) == list(gold)


def test_oversize_word_uses_one_unknown_piece_and_keeps_source_interval() -> None:
    """Replace an indivisible oversized word without dropping its offsets or taking a subspan."""
    text = "mã z/z/z/z/z/z"
    words = _words(text)
    gold = (_span(words[1], "ID"),)
    features = build_features(
        Note("n4", "fixture", text, gold), words, ToyBpe(), max_length=6, overlap_tokens=1
    )
    (window,) = features.windows
    assert window.input_ids[2] == ToyBpe.unk_token_id
    assert features.oversize_words == 1
    assert window.labels[2] == TAG_IDS["B-ID"]


def test_strict_decoder_drops_orphan_and_wrong_label_continuations() -> None:
    """Prevent an unpaired continuation from becoming an invented positive span."""
    words = _words("Tên An mã ID thứ hai")
    tags = "I-NAME B-PHONE I-ID I-PHONE B-NAME I-NAME".split()
    assert decode_word_tags(words, [TAG_IDS[tag] for tag in tags]) == [
        _span(words[1], "PHONE"),
        Span(words[4].source.start, words[5].source.end, "NAME"),
    ]


def test_misaligned_source_and_incomplete_prediction_raise() -> None:
    """Surface missing source coverage or inference entries instead of dropping them silently."""
    note = Note("n5", "fixture", "🙂 An", ())
    with pytest.raises(ValueError, match="không phủ"):
        build_features(note, [_word(note.text, "An")], ToyBpe())
    with pytest.raises(ValueError, match="Thiếu dự đoán"):
        merge_window_tags([], [], 1)
