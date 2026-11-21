# ml/upstream/smoke.py — Smoke one real upstream engine on the shared synthetic fixture.
import argparse
import json
import os
import sys
from collections.abc import Iterable
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import TypedDict

from ml.upstream.adapters import (
    SmokeError,
    Span,
    philter_positions,
    presidio_positions,
    pydeid_positions,
)

# Hand-authored for this smoke. The phone number uses the reserved fictional 555-01xx range.
PHONE = "202-555-0147"
FIXTURE = f"Patient: Alice Example. DOB: 03/14/1982. Phone: {PHONE}. Follow-up in two weeks."


class Position(TypedDict):
    """Position represents one half-open region in Unicode code points."""

    start: int
    end: int


def coverage(note: str, spans: Iterable[Span]) -> list[Position]:
    """coverage validates spans and returns sorted, disjoint non-whitespace coverage regions."""
    selected: set[int] = set()
    for start, end in spans:
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(note):
            raise SmokeError("Engine returned offsets outside the synthetic fixture.")
        selected.update(index for index in range(start, end) if not note[index].isspace())
    positions: list[Position] = []
    for index in sorted(selected):
        if positions and positions[-1]["end"] == index:
            positions[-1]["end"] = index + 1
        else:
            positions.append({"start": index, "end": index + 1})
    return positions


def main() -> int:
    """main runs the requested engine against the built-in fixture and emits positions as JSON."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engine", choices=("presidio", "philter", "pydeid"))
    parser.add_argument("--philter-root", type=Path)
    parser.add_argument("--nltk-data", type=Path)
    args = parser.parse_args()
    if args.engine == "philter" and (args.philter_root is None or args.nltk_data is None):
        parser.error("philter requires --philter-root and --nltk-data")

    try:
        with (
            open(os.devnull, "w", encoding="utf-8") as quiet,
            redirect_stdout(quiet),
            redirect_stderr(quiet),
        ):
            if args.engine == "presidio":
                spans = presidio_positions(FIXTURE)
            elif args.engine == "pydeid":
                spans = pydeid_positions(FIXTURE)
            else:
                spans = philter_positions(FIXTURE, args.philter_root, args.nltk_data.resolve())
        positions = coverage(FIXTURE, spans)
        covered = {
            index for region in positions for index in range(region["start"], region["end"])
        }
        phone_start = FIXTURE.index(PHONE)
        digits = {phone_start + offset for offset, char in enumerate(PHONE) if char.isdigit()}
        if not digits.issubset(covered):
            raise SmokeError("Engine did not cover every digit of the synthetic phone number.")
    except SmokeError as error:
        print(f"{args.engine}: {error}", file=sys.stderr)
        return 1
    except Exception as error:
        print(f"{args.engine}: upstream smoke failed ({type(error).__name__}).", file=sys.stderr)
        return 1

    print(json.dumps(positions))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
