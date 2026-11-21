# ml/upstream/adapters.py — Run the pinned upstream engines and extract original positions.
import json
import os
import subprocess
import sys
from importlib.metadata import distribution, version
from pathlib import Path
from tempfile import TemporaryDirectory

from ml.upstream.resources import tagger_ready

Span = tuple[int, int]
MODEL = "en_core_web_sm"
PYDEID_URL = "https://github.com/GEMINI-Medicine/pyDeid.git"
PYDEID_REVISION = "f93d2ddb1fd857236b2d3b4b761af2b8028c7281"


class SmokeError(Exception):
    """SmokeError carries a diagnostic that is safe to report without the note."""


def presidio_positions(note: str) -> list[Span]:
    """presidio_positions analyzes an English synthetic note and returns Analyzer spans."""
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
    return [(hit.start, hit.end) for hit in analyzer.analyze(text=note, language="en")]


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
    if not (checkout / "configs" / "philter_delta.json").is_file():
        raise SmokeError("Philter checkout is missing configs/philter_delta.json.")
    if not tagger_ready(nltk_data):
        raise SmokeError("Philter POS tagger is missing or differs from the resource pin.")

    with TemporaryDirectory(prefix="medshield-synthetic-") as scratch:
        input_dir, output_dir = Path(scratch) / "input", Path(scratch) / "output"
        input_dir.mkdir()
        output_dir.mkdir()
        (input_dir / "fixture.txt").write_bytes(note.encode("ascii"))
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                "-X",
                "utf8",
                "main.py",
                "-i",
                str(input_dir),
                "-o",
                str(output_dir),
                "-f",
                "configs/philter_delta.json",
                "--prod=True",
                "--outputformat",
                "asterisk",
            ],
            cwd=checkout,
            env={**os.environ, "NLTK_DATA": str(nltk_data)},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=90,
        )
        if result.returncode != 0:
            raise SmokeError(f"Philter CLI exited with code {result.returncode}.")
        mask = (output_dir / "fixture.txt").read_text(encoding="utf-8")

    if len(mask) != len(note):
        raise SmokeError("Philter mask changed the synthetic note length.")
    positions = []
    for index, (original, masked) in enumerate(zip(note, mask, strict=True)):
        if original == masked:
            continue
        if masked != "*" or original.isspace():
            raise SmokeError("Philter output differs from an aligned asterisk mask.")
        positions.append((index, index + 1))
    return positions
