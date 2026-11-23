# ml/upstream/regions.py — Validate original spans and compute non-whitespace region coverage.
from collections.abc import Iterable
from typing import TypedDict

from ml.upstream.adapters import SmokeError, Span


class Position(TypedDict):
    """Position represents a half-open region in Unicode code points."""

    start: int
    end: int


def covered_positions(note: str, spans: Iterable[Span]) -> set[int]:
    """covered_positions returns the distinct non-whitespace code points from validated spans."""
    selected: set[int] = set()
    for start, end in spans:
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(note):
            raise SmokeError("Engine returned offsets outside the synthetic note.")
        selected.update(index for index in range(start, end) if not note[index].isspace())
    return selected


def contiguous_positions(selected: Iterable[int]) -> list[Position]:
    """contiguous_positions compacts a set of code-point indices into sorted disjoint regions."""
    positions: list[Position] = []
    for index in sorted(selected):
        if positions and positions[-1]["end"] == index:
            positions[-1]["end"] = index + 1
        else:
            positions.append({"start": index, "end": index + 1})
    return positions
