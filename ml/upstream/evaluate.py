# ml/upstream/evaluate.py — Run the three English evaluation workers and publish their artifact.
import argparse
import json
import subprocess
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

from ml.upstream.adapters import PYDEID_REVISION, SmokeError
from ml.upstream.english import (
    EnglishNote,
    corpus_metadata,
    gold_positions,
    load_corpus,
    score_regions,
)
from ml.upstream.resources import TAGGER_SHA256
from ml.upstream.worker import PHILTER_REVISION, PYTHON, WorkerResult

REPRODUCE = [
    r"powershell.exe -NoProfile -File .\scripts\setup-upstream.ps1",
    r"powershell.exe -NoProfile -File .\scripts\evaluate-upstream.ps1",
]
ENGINE_CONFIG = {
    "presidio": {
        "source": "https://github.com/data-privacy-stack/presidio",
        "reference_revision": "9fc7774ed74faa0afd5ffb36da63e77b9a2f8c30",
        "config": {"language": "en", "nlp_engine": "spacy", "model": "en_core_web_sm"},
    },
    "philter": {
        "source": "https://github.com/BCHSI/philter-ucsf",
        "source_revision": PHILTER_REVISION,
        "config": {
            "filters": "configs/philter_delta.json",
            "pos_tagger_sha256": TAGGER_SHA256,
            "format": "asterisk",
            "input_encoding": "utf-8",
            "offset_projection": "universal newlines to original code points",
        },
    },
    "pydeid": {
        "source": "https://github.com/GEMINI-Medicine/pyDeid",
        "source_revision": PYDEID_REVISION,
        "config": {"named_entity_recognition": False},
    },
}
METRIC_KEYS = ("tp", "fp", "fn", "precision", "recall", "f1", "support")


def _worker(engine: str, upstream_root: Path) -> WorkerResult:
    """Run one isolated interpreter and parse its positional result."""
    environment = Path(".venv-upstream-g2") / engine
    interpreter = environment / "Scripts" / "python.exe"
    if not interpreter.is_file():
        raise SmokeError("Isolated engine environment is missing; run setup-upstream.ps1.")
    process = subprocess.run(
        [
            str(interpreter.resolve()),
            "-E",
            "-s",
            "-B",
            "-m",
            "ml.upstream.worker",
            engine,
            "--philter-root",
            str(upstream_root / "philter"),
            "--nltk-data",
            str((environment / "nltk_data").resolve()),
        ],
        capture_output=True,
        encoding="utf-8",
        check=False,
        timeout=240,
    )
    if process.returncode:
        diagnostic = process.stderr.strip().removeprefix("Unavailable: ")
        if not process.stderr.startswith("Unavailable: ") or "\n" in diagnostic:
            diagnostic = f"Worker exited with code {process.returncode}."
        raise SmokeError(diagnostic)
    result: WorkerResult = json.loads(process.stdout)
    return result


def _result(engine: str, notes: list[EnglishNote], upstream_root: Path) -> dict[str, object]:
    """Return a complete scoring row or a diagnostic with all metrics unmeasured."""
    lock = Path("ml/upstream") / f"{engine}.lock.txt"
    config = {
        **ENGINE_CONFIG[engine],
        "python_pin": PYTHON[engine],
        "lock_file": lock.as_posix(),
        "lock_sha256": sha256(lock.read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
    }
    base: dict[str, object] = {
        "language": "en",
        "method": engine,
        "unit": "redaction_region",
        "notes": len(notes),
        "gold_entities": sum(len(note["entities"]) for note in notes),
        "by_label": {},
        "environment": config,
        "reproduce": REPRODUCE,
    }
    try:
        worker = _worker(engine, upstream_root)
        scores = score_regions(notes, worker["predictions"])
    except (SmokeError, OSError, ValueError, subprocess.TimeoutExpired) as error:
        reason = str(error) if isinstance(error, SmokeError) else type(error).__name__
        return {
            **base,
            "status": "unavailable",
            "reason": reason,
            "micro": dict.fromkeys(METRIC_KEYS)
            | {"support": sum(len(gold_positions(note)) for note in notes)},
            "notes_with_fn": None,
            "examples": [],
        }
    return {
        **base,
        "status": "available",
        **scores,
        "environment": {**config, "actual": worker["runtime"]},
    }


def _write_artifact(path: Path, artifact: dict[str, object]) -> None:
    """Publish a complete UTF-8 JSON artifact atomically in the requested directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(artifact, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    with TemporaryDirectory(dir=path.parent) as directory:
        staged = Path(directory) / path.name
        staged.write_bytes(payload.encode("utf-8"))
        staged.replace(path)


def main() -> int:
    """main evaluates all three engines, publishes the result rows and reports failures."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    notes = load_corpus()
    results = [_result(engine, notes, args.upstream_root.resolve()) for engine in PYTHON]
    artifact = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "dataset": corpus_metadata(notes),
        "score_definition": "Micro counts of non-whitespace Unicode code points in region unions",
        "reproduce": REPRODUCE,
        "results": results,
    }
    _write_artifact(args.output, artifact)
    for row in results:
        print(f"{row['method']}: {row['status']}")
    return int(any(row["status"] == "unavailable" for row in results))


if __name__ == "__main__":
    raise SystemExit(main())
