# ml/upstream/worker.py — Run one independent upstream environment over the locked English notes.
import argparse
import json
import os
import platform
import subprocess
import sys
from contextlib import redirect_stderr, redirect_stdout
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
from typing import TypedDict

from ml.upstream.adapters import (
    PHILTER_CONFIG,
    SmokeError,
    Span,
    philter_batch,
    presidio_predictor,
    pydeid_positions,
)
from ml.upstream.english import load_corpus

PHILTER_REVISION = "4da3cf31c9bfbfd66c66b141c45ba7a47628dd0a"
PYTHON = {"presidio": "3.11.7", "philter": "3.10.20", "pydeid": "3.11.7"}
PACKAGES = {
    "presidio": ("presidio-analyzer", "spacy", "en-core-web-sm", "numpy"),
    "philter": ("nltk", "chardet", "numpy", "pandas", "xmltodict"),
    "pydeid": ("pydeid", "spacy", "numpy", "click", "setuptools"),
}


class WorkerResult(TypedDict):
    """WorkerResult carries actual runtime versions and positional predictions keyed by note ID."""

    runtime: dict[str, object]
    predictions: dict[str, list[Span]]


def _philter_revision(checkout: Path) -> str:
    """Verify the upstream origin and ensure tracked source matches the pinned revision."""
    git = ["git", "-C", str(checkout)]
    origin = subprocess.check_output([*git, "remote", "get-url", "origin"], text=True).strip()
    revision = subprocess.check_output([*git, "rev-parse", "HEAD"], text=True).strip()
    changes = subprocess.check_output([*git, "status", "--porcelain", "-uno"], text=True)
    if origin != "https://github.com/BCHSI/philter-ucsf.git" or revision != PHILTER_REVISION:
        raise SmokeError("Philter checkout origin or revision differs from the pin.")
    if changes:
        raise SmokeError("Philter checkout has tracked changes.")
    return revision


def run(engine: str, checkout: Path, nltk_data: Path) -> WorkerResult:
    """run evaluates one engine against all pinned notes and returns positions and versions."""
    python = platform.python_version()
    if python != PYTHON[engine]:
        raise SmokeError(f"Expected Python {PYTHON[engine]}; found {python}.")
    runtime: dict[str, object] = {
        "python": python,
        "system": platform.system(),
        "machine": platform.machine(),
        "packages": {package: version(package) for package in PACKAGES[engine]},
    }
    notes = {note["note_id"]: note["text"] for note in load_corpus()}
    if engine == "philter":
        runtime["source_revision"] = _philter_revision(checkout)
        # Normalize checkout line endings for a stable digest across Git configurations.
        config = (checkout / PHILTER_CONFIG).read_bytes().replace(b"\r\n", b"\n")
        runtime["config_sha256"] = sha256(config).hexdigest()
        predictions = philter_batch(notes, checkout, nltk_data)
    else:
        predict = presidio_predictor() if engine == "presidio" else pydeid_positions
        predictions = {note_id: predict(note) for note_id, note in notes.items()}
    return {"runtime": runtime, "predictions": predictions}


def main() -> int:
    """main runs a batch worker and exposes a safe failure reason without upstream output."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engine", choices=tuple(PYTHON))
    parser.add_argument("--philter-root", type=Path, required=True)
    parser.add_argument("--nltk-data", type=Path, required=True)
    args = parser.parse_args()

    try:
        with (
            open(os.devnull, "w", encoding="utf-8") as quiet,
            redirect_stdout(quiet),
            redirect_stderr(quiet),
        ):
            result = run(args.engine, args.philter_root, args.nltk_data)
    except SmokeError as error:
        print(f"Unavailable: {error}", file=sys.stderr)
        return 1
    except Exception as error:
        print(f"Unavailable: worker failed ({type(error).__name__}).", file=sys.stderr)
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
