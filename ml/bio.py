# ml/bio.py — Convert exact entity spans to BIO sequences and back.
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import chain
from typing import Literal, cast

from ml.tokenization import Token

GOLD_LABELS = ("NAME", "DOB", "PHONE", "ID", "ADDR")
ModelLabel = Literal["NAME", "ADDR"]
MODEL_LABELS = ("NAME", "ADDR")
MODEL_TAGS = {"O", *(prefix + label for prefix in ("B-", "I-") for label in MODEL_LABELS)}


@dataclass(frozen=True, slots=True)
class Span:
    """Span stores an exact gold or decoded half-open code point interval and its label."""

    start: int
    end: int
    label: str


@dataclass(frozen=True, slots=True)
class DecodedSpan:
    """DecodedSpan identifies a reconstructed span and its contributing token range."""

    span: Span
    first_token: int
    end_token: int

    @property
    def label(self) -> ModelLabel:
        """Return the model label guaranteed by decode_bio validation."""
        return cast(ModelLabel, self.span.label)


def encode_bio(tokens: Sequence[Token], spans: Sequence[Span]) -> list[str]:
    """Encode model labels as BIO and reject any gold span that cuts a token boundary."""
    starts = {token.start: index for index, token in enumerate(tokens)}
    ends = {token.end: index for index, token in enumerate(tokens)}
    tags = ["O"] * len(tokens)
    for span in spans:
        first, last = starts.get(span.start), ends.get(span.end)
        if first is None or last is None or first > last:
            raise ValueError("Gold span does not align with token boundaries.")
        if span.label in MODEL_LABELS:
            tags[first] = f"B-{span.label}"
            tags[first + 1 : last + 1] = [f"I-{span.label}"] * (last - first)
    return tags


def decode_bio(tokens: Sequence[Token], tags: Sequence[str]) -> list[DecodedSpan]:
    """Decode tags over source offsets; a stray I-tag opens a new span of its own type."""
    if len(tokens) != len(tags) or any(tag not in MODEL_TAGS for tag in tags):
        raise ValueError("Invalid BIO sequence.")
    spans: list[DecodedSpan] = []
    label = ""
    first = 0
    for index, tag in enumerate(chain(tags, ("O",))):
        if label and tag == f"I-{label}":
            continue
        if label:
            span = Span(tokens[first].start, tokens[index - 1].end, label)
            spans.append(DecodedSpan(span, first, index))
        label = tag[2:]
        first = index
    return spans
