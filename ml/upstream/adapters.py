# ml/upstream/adapters.py — Run the pinned upstream engines and extract original positions.
import json
import os
import subprocess
import sys
from collections.abc import Callable, Mapping
from importlib.metadata import distribution, version
from pathlib import Path
from tempfile import TemporaryDirectory

from ml.upstream.resources import tagger_ready

Span = tuple[int, int]
MODEL = "en_core_web_sm"
PYDEID_URL = "https://github.com/GEMINI-Medicine/pyDeid.git"
PYDEID_REVISION = "f93d2ddb1fd857236b2d3b4b761af2b8028c7281"
PHILTER_CONFIG = "configs/philter_delta.json"
PHILTER_UTF8_ENTRY = """\
import main

class Utf8Philter(main.Philter):
    def detect_encoding(self, path):
        return {"encoding": "utf-8"}

main.Philter = Utf8Philter
main.main()
"""


class SmokeError(Exception):
    """SmokeError carries a diagnostic that is safe to report without the note."""


def presidio_predictor() -> Callable[[str], list[Span]]:
    """presidio_predictor loads one Analyzer and returns a callable for English note positions."""
    from presidio_analyzer import AnalyzerEngine
    from presidio_analyzer.nlp_engine import NlpEngineProvider

    if version("presidio-analyzer") != "2.2.366" or version(MODEL) != "3.7.1":
        raise SmokeError("Presidio Analyzer or English model version differs from the pin.")
    config = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "en", "model_name": MODEL}],
    }
    nlp = NlpEngineProvider(nlp_configuration=config).create_engine()
    analyzer = AnalyzerEngine(nlp_engine=nlp, supported_languages=["en"])

    def predict(note: str) -> list[Span]:
        """predict returns original spans from the same loaded Analyzer for one note."""
        return [(hit.start, hit.end) for hit in analyzer.analyze(text=note, language="en")]

    return predict


def presidio_positions(note: str) -> list[Span]:
    """presidio_positions runs a standalone English smoke using a fresh Analyzer."""
    return presidio_predictor()(note)


def pydeid_positions(note: str) -> list[Span]:
    """pydeid_positions runs GEMINI rules and extracts only the original surrogate offsets."""
    package = distribution("pydeid")
    provenance = json.loads(package.read_text("direct_url.json") or "{}")
    if (
        package.version != "1.0.1"
        or provenance.get("url") != PYDEID_URL
        or provenance.get("vcs_info", {}).get("commit_id") != PYDEID_REVISION
    ):
        raise SmokeError("GEMINI pyDeid version or Git provenance differs from the pin.")

    from pyDeid import deid_string

    surrogates, _ = deid_string(note, named_entity_recognition=False)
    return [(hit["phi_start"], hit["phi_end"]) for hit in surrogates]


def philter_positions(note: str, checkout: Path, nltk_data: Path) -> list[Span]:
    """philter_positions runs the UCSF CLI on the fixed ASCII fixture and reads mask positions."""
    if not note.isascii() or "*" in note or "\r" in note:
        raise SmokeError("The Philter smoke fixture must be ASCII with LF and no asterisks.")
    return philter_batch({"fixture": note}, checkout, nltk_data, explicit_utf8=False)["fixture"]


def philter_batch(
    notes: Mapping[str, str],
    checkout: Path,
    nltk_data: Path,
    *,
    explicit_utf8: bool = True,
) -> dict[str, list[Span]]:
    """philter_batch runs the UCSF CLI on synthetic notes and maps masks to original positions."""
    if not (checkout / PHILTER_CONFIG).is_file():
        raise SmokeError("Philter checkout is missing configs/philter_delta.json.")
    if not tagger_ready(nltk_data):
        raise SmokeError("Philter POS tagger is missing or differs from the resource pin.")

    with TemporaryDirectory(prefix="medshield-synthetic-") as scratch:
        input_dir, output_dir = Path(scratch) / "input", Path(scratch) / "output"
        input_dir.mkdir()
        output_dir.mkdir()
        files = {note_id: f"{index}.txt" for index, note_id in enumerate(notes)}
        for note_id, note in notes.items():
            (input_dir / files[note_id]).write_bytes(note.encode("utf-8"))
        entry = ["-c", PHILTER_UTF8_ENTRY] if explicit_utf8 else ["main.py"]
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                "-X",
                "utf8",
                *entry,
                "-i",
                str(input_dir),
                "-o",
                str(output_dir),
                "-f",
                PHILTER_CONFIG,
                "--prod=True",
                "--outputformat",
                "asterisk",
            ],
            cwd=checkout,
            env={**os.environ, "NLTK_DATA": str(nltk_data)},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=180,
        )
        if result.returncode != 0:
            raise SmokeError(f"Philter CLI exited with code {result.returncode}.")
        return {
            note_id: _mask_positions(
                note, (output_dir / files[note_id]).read_text(encoding="utf-8")
            )
            for note_id, note in notes.items()
        }


def _mask_positions(note: str, mask: str) -> list[Span]:
    """Map universal newlines in the CLI mask back to untouched original code point indexes."""
    original_indices = [index for index in range(len(note)) if note[index : index + 2] != "\r\n"]
    if len(mask) != len(original_indices):
        raise SmokeError("Philter mask changed the synthetic note length.")
    positions = []
    for index, masked in zip(original_indices, mask, strict=True):
        original = "\n" if note[index] == "\r" else note[index]
        if original == masked:
            continue
        if masked != "*" or original.isspace():
            raise SmokeError("Philter output differs from an aligned asterisk mask.")
        positions.append((index, index + 1))
    return positions
