# ml/upstream/resources.py — Install and verify the pinned English NLTK tagger for Philter.
import argparse
import hashlib
from io import BytesIO
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

TAGGER = "averaged_perceptron_tagger_eng"
TAGGER_URL = (
    f"https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/taggers/{TAGGER}.zip"
)
TAGGER_SHA256 = "6025f530624335c67d6547d44757b357b4e79bae030a0383e9887a92c1718f0b"
TAGGER_FILES = {
    "classes": "d152ffa69d45b8357276341a3d592c6c025911d52ec0d9068d4f382560dd48b6",
    "tagdict": "4c713731cb06727736962bc8cd94ad919217a040e76691059af99bc0c2c9c246",
    "weights": "789e8e35f6fac656d9b7eccea29ba4e8a137cbb5b525dd31f39e4291a9e80832",
}


def tagger_ready(data_dir: Path) -> bool:
    """tagger_ready checks the three installed model files against their expected hashes."""
    for part, digest in TAGGER_FILES.items():
        path = data_dir / "taggers" / TAGGER / f"{TAGGER}.{part}.json"
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            return False
    return True


def install_tagger(data_dir: Path) -> None:
    """install_tagger downloads and verifies the official ZIP when pinned files are missing."""
    if tagger_ready(data_dir):
        return
    with urlopen(TAGGER_URL, timeout=60) as response:
        payload = response.read()
    if hashlib.sha256(payload).hexdigest() != TAGGER_SHA256:
        raise ValueError("NLTK tagger archive SHA-256 differs from the pin.")
    target = data_dir / "taggers" / TAGGER
    target.mkdir(parents=True, exist_ok=True)
    with ZipFile(BytesIO(payload)) as archive:
        for part in TAGGER_FILES:
            name = f"{TAGGER}.{part}.json"
            (target / name).write_bytes(archive.read(f"{TAGGER}/{name}"))
    if not tagger_ready(data_dir):
        raise ValueError("Extracted NLTK tagger files differ from the pin.")


def main() -> None:
    """main installs the tagger into the resource directory provided on the command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data_dir", type=Path)
    install_tagger(parser.parse_args().data_dir)


if __name__ == "__main__":
    main()
