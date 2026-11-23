# ml/tokenization.py — Tokenize Unicode text while preserving source offsets.
from dataclasses import dataclass
from unicodedata import category

TOKENIZER_VERSION = 1


@dataclass(frozen=True, slots=True)
class Token:
    """Token stores the half-open code point interval of one source token."""

    start: int
    end: int


def tokenize(text: str) -> list[Token]:
    """Tokenize source text into words, numbers and symbols; keep combining marks attached."""
    tokens: list[Token] = []
    start = 0
    end = 0
    kind = ""
    for index, char in enumerate(text):
        current = category(char)[0]
        if char.isspace():
            current = ""
        if kind and (current == "M" or (current == kind and kind in {"L", "N"})):
            end = index + 1
            continue
        if kind:
            tokens.append(Token(start, end))
        start, end, kind = index, index + 1, current
    if kind:
        tokens.append(Token(start, end))
    return tokens
