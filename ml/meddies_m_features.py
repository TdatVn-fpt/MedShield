# ml/meddies_m_features.py — Build overlapping BPE windows and decode source-offset BIO spans.
from bisect import bisect_left, bisect_right
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import accumulate
from typing import Protocol

from ml.bio import GOLD_LABELS, Span
from ml.dataset import Note
from ml.meddies_m_segment import SegmentedWord

BIO_TAGS = ("O", *(f"{prefix}-{label}" for label in GOLD_LABELS for prefix in ("B", "I")))
TAG_IDS = {tag: index for index, tag in enumerate(BIO_TAGS)}
IGNORE_INDEX = -100
MAX_LENGTH = 256


class WordTokenizer(Protocol):
    """Provide the slow PhoBERT tokenizer operations needed for whole-word windows."""

    @property
    def unk_token_id(self) -> int | None:
        """Return the model ID used for a word that cannot fit intact in a window."""
        ...

    def encode(self, text: str, *, add_special_tokens: bool) -> list[int]:
        """Encode one segmented word using native BPE without resegmentation."""
        ...

    def build_inputs_with_special_tokens(self, token_ids_0: list[int]) -> list[int]:
        """Add the model's special tokens to an already encoded window."""
        ...

    def get_special_tokens_mask(self, token_ids_0: list[int]) -> list[int]:
        """Mark inserted special positions for an otherwise unwrapped window."""
        ...


@dataclass(frozen=True, slots=True)
class FeatureWindow:
    """Hold model input IDs, loss targets, and owned first-piece positions."""

    input_ids: tuple[int, ...]
    labels: tuple[int, ...]
    owned_positions: tuple[tuple[int, int], ...]


@dataclass(frozen=True, slots=True)
class WordFeatures:
    """Hold windows and diagnostics without altering the original note or gold entities."""

    windows: tuple[FeatureWindow, ...]
    excluded_support: dict[str, int]
    oversize_words: int


def _validate_words(text: str, words: Sequence[SegmentedWord]) -> None:
    """Require ordered source intervals that cover all non-whitespace input."""
    previous = 0
    for word in words:
        start, end = word.source.start, word.source.end
        if (
            not 0 <= previous <= start < end <= len(text)
            or text[previous:start].strip()
            or not word.value
            or any(char.isspace() for char in word.value)
        ):
            raise ValueError("Từ đã tách không phủ đúng văn bản nguồn.")
        previous = end
    if text[previous:].strip():
        raise ValueError("Từ đã tách bỏ sót ký tự trong văn bản nguồn.")


def _target_tags(note: Note, words: Sequence[SegmentedWord]) -> tuple[list[int], dict[str, int]]:
    """Encode aligned gold and mask all touched words of unrepresentable regions."""
    starts = [word.source.start for word in words]
    ends = [word.source.end for word in words]
    by_start = {offset: index for index, offset in enumerate(starts)}
    by_end = {offset: index for index, offset in enumerate(ends)}
    labels = [TAG_IDS["O"]] * len(words)
    excluded: Counter[str] = Counter()
    masked: set[int] = set()
    for entity in note.entities:
        first = by_start.get(entity.start)
        last = by_end.get(entity.end)
        if first is None or last is None or first > last:
            excluded[entity.label] += 1
            masked.update(range(bisect_right(ends, entity.start), bisect_left(starts, entity.end)))
            continue
        labels[first] = TAG_IDS[f"B-{entity.label}"]
        labels[first + 1 : last + 1] = [TAG_IDS[f"I-{entity.label}"]] * (last - first)
    for position in masked:
        labels[position] = IGNORE_INDEX
    return labels, {label: excluded[label] for label in GOLD_LABELS}


def _encode_words(
    words: Sequence[SegmentedWord], tokenizer: WordTokenizer, payload_limit: int
) -> tuple[list[list[int]], int]:
    """Encode words whole and use one unknown piece if a word exceeds the window budget."""
    pieces = []
    oversize = 0
    for word in words:
        ids = tokenizer.encode(word.value, add_special_tokens=False)
        if not ids or len(ids) > payload_limit:
            if tokenizer.unk_token_id is None:
                raise ValueError("Bộ mã hóa thiếu mã từ không nhận diện được.")
            oversize += len(ids) > payload_limit
            ids = [tokenizer.unk_token_id]
        pieces.append(ids)
    return pieces, oversize


def _window_ranges(
    offsets: list[int], payload_limit: int, overlap_tokens: int
) -> list[tuple[int, int]]:
    """Choose whole-word windows with bounded piece overlap and forward progress."""
    ranges = []
    first = 0
    word_count = len(offsets) - 1
    while first < word_count:
        end_piece = offsets[first] + payload_limit
        last = bisect_right(offsets, end_piece, lo=first + 1) - 1
        ranges.append((first, last))
        if last == word_count:
            break
        overlap_start = offsets[last] - overlap_tokens
        first = bisect_left(offsets, overlap_start, lo=first + 1, hi=last + 1)
    return ranges


def _owner_windows(offsets: list[int], ranges: list[tuple[int, int]]) -> list[int]:
    """Assign each word to its widest minimum context, resolving ties to earlier windows."""
    owners = [-1] * (len(offsets) - 1)
    best_context = [-1] * len(owners)
    for index, (first, last) in enumerate(ranges):
        for word in range(first, last):
            left = offsets[word] - offsets[first]
            right = offsets[last] - offsets[word + 1]
            context = min(left, right)
            if context > best_context[word]:
                owners[word] = index
                best_context[word] = context
    return owners


def build_features(
    note: Note,
    words: Sequence[SegmentedWord],
    tokenizer: WordTokenizer,
    *,
    max_length: int = MAX_LENGTH,
    overlap_tokens: int = 48,
) -> WordFeatures:
    """Build owner-tagged BIO windows under a total model limit including special tokens."""
    _validate_words(note.text, words)
    payload_limit = max_length - len(tokenizer.build_inputs_with_special_tokens([]))
    if not 1 <= max_length <= MAX_LENGTH or not 0 <= overlap_tokens < payload_limit:
        raise ValueError("Giới hạn cửa sổ hoặc độ chồng lấn BPE không hợp lệ.")
    tags, excluded = _target_tags(note, words)
    pieces, oversize = _encode_words(words, tokenizer, payload_limit)
    offsets = list(accumulate(map(len, pieces), initial=0))
    ranges = _window_ranges(offsets, payload_limit, overlap_tokens)
    owners = _owner_windows(offsets, ranges)
    windows = []
    for index, (first, last) in enumerate(ranges):
        owned_words = [word for word in range(first, last) if owners[word] == index]
        if not owned_words:
            continue
        raw = [piece for word in pieces[first:last] for piece in word]
        input_ids = tokenizer.build_inputs_with_special_tokens(raw)
        special = tokenizer.get_special_tokens_mask(raw)
        positions = [position for position, flag in enumerate(special) if flag == 0]
        if (
            len(special) != len(input_ids)
            or len(input_ids) > max_length
            or any(flag not in {0, 1} for flag in special)
            or [input_ids[position] for position in positions] != raw
        ):
            raise ValueError("Vị trí token đặc biệt không khớp đoạn BPE.")
        labels = [IGNORE_INDEX] * len(input_ids)
        owned = []
        for word in owned_words:
            position = positions[offsets[word] - offsets[first]]
            labels[position] = tags[word]
            owned.append((position, word))
        windows.append(FeatureWindow(tuple(input_ids), tuple(labels), tuple(owned)))
    return WordFeatures(tuple(windows), excluded, oversize)


def merge_window_tags(
    windows: Sequence[FeatureWindow], window_tag_ids: Sequence[Sequence[int]], word_count: int
) -> list[int]:
    """Gather a single prediction per original word from the window that owns its first piece."""
    if word_count < 0:
        raise ValueError("Số từ nguồn không hợp lệ.")
    word_ids = [IGNORE_INDEX] * word_count
    for window, tag_ids in zip(windows, window_tag_ids, strict=True):
        if len(tag_ids) < len(window.input_ids):
            raise ValueError("Thiếu nhãn dự đoán cho cửa sổ BPE.")
        for position, word in window.owned_positions:
            if (
                not 0 <= position < len(window.input_ids)
                or not 0 <= word < word_count
                or word_ids[word] != IGNORE_INDEX
            ):
                raise ValueError("Từ nguồn phải thuộc đúng một cửa sổ BPE.")
            tag = tag_ids[position]
            if type(tag) is not int or not 0 <= tag < len(BIO_TAGS):
                raise ValueError("Nhãn dự đoán BIO ngoài danh sách đã đăng ký.")
            word_ids[word] = tag
    if IGNORE_INDEX in word_ids:
        raise ValueError("Thiếu dự đoán cho từ trong văn bản nguồn.")
    return word_ids


def decode_word_tags(words: Sequence[SegmentedWord], tag_ids: Sequence[int]) -> list[Span]:
    """Decode strict BIO in source order, discarding I-tags without a matching open B-tag."""
    if len(words) != len(tag_ids) or any(
        type(tag) is not int or not 0 <= tag < len(BIO_TAGS) for tag in tag_ids
    ):
        raise ValueError("Dãy nhãn BIO không khớp số từ hoặc tập nhãn.")
    spans: list[Span] = []
    active = ""
    start = end = previous = 0
    for word, tag_id in zip(words, tag_ids, strict=True):
        source, tag = word.source, BIO_TAGS[tag_id]
        if not 0 <= previous <= source.start < source.end:
            raise ValueError("Offsets từ nguồn không theo thứ tự hoặc bị chồng lấn.")
        previous = source.end
        if active and tag == f"I-{active}":
            end = source.end
            continue
        if active:
            spans.append(Span(start, end, active))
        active = tag[2:] if tag.startswith("B-") else ""
        start, end = source.start, source.end
    if active:
        spans.append(Span(start, end, active))
    return spans
