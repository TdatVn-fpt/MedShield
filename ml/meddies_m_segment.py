# ml/meddies_m_segment.py — Align the pinned Vietnamese word segmenter with source code points.
from dataclasses import dataclass
from hashlib import file_digest
from pathlib import Path
from subprocess import TimeoutExpired, run
from tempfile import TemporaryDirectory

from apps.api.adapters.vi_names_places import folded_text
from ml.tokenization import Token

JAR = "VnCoreNLP-1.2.jar"
SEGMENTER_FILES = {
    JAR: "9e2811cdbc2ddfc71d04be5dc36e185c88dcd1ad4d5d69e4ff2e1369dccf7793",
    "models/wordsegmenter/vi-vocab": (
        "0a47c5b55bbce163029d37730a67b9479740388695c29c106c112b815613eaa5"
    ),
    "models/wordsegmenter/wordsegmenter.rdr": (
        "9e62f96bd93e37a24f364238e8d8ae986fa5dad6dbc9f4eae622ab3651b7fa06"
    ),
}
BOUNDARY = "ZMEDSHIELDZNOTEZBOUNDARYZ"


@dataclass(frozen=True, slots=True)
class SegmentedWord:
    """Store a model-side segmented word and its half-open original interval."""

    value: str
    source: Token


def _aligned_words(text: str, words: list[str]) -> list[SegmentedWord] | None:
    """Match words in order, allowing underscores generated from source whitespace."""
    original, starts, ends = folded_text(text)
    offset = source_end = 0
    result = []
    for word in words:
        word = "_".join(word.split())
        if not word:
            continue
        while offset < len(original) and original[offset].isspace():
            offset += 1
        start = offset
        folded, _, _ = folded_text(word)
        for char in folded:
            if char == "_" and offset < len(original) and original[offset].isspace():
                while offset < len(original) and original[offset].isspace():
                    offset += 1
            else:
                if offset >= len(original) or original[offset] != char:
                    return None
                offset += 1
        if offset == start or original[offset - 1].isspace():
            return None
        if offset < len(starts) and starts[offset] == starts[offset - 1]:
            return None
        source_start = starts[start]
        if text[source_end:source_start].strip():
            return None
        source_end = ends[offset - 1]
        result.append(SegmentedWord(word, Token(source_start, source_end)))
    return result if not text[source_end:].strip() else None


def _segmented_rows(output: str, expected: int) -> list[list[str]]:
    """Parse VnCoreNLP TSV and require exactly one section for each input note."""
    groups: list[list[str]] = [[]]
    for line in output.splitlines():
        if not line.strip():
            continue
        fields = line.split("\t", maxsplit=2)
        if len(fields) != 3 or not fields[0].isdigit() or not fields[1]:
            raise ValueError("Đầu ra tách từ không đúng dạng TSV của VnCoreNLP.")
        if fields[1] == BOUNDARY:
            groups.append([])
        else:
            groups[-1].append(fields[1])
    if len(groups) != expected:
        raise ValueError("Số ghi chú sau tách từ khác số ghi chú đầu vào.")
    return groups


def segment_notes(texts: list[str], segmenter: Path) -> list[list[SegmentedWord] | None]:
    """Run the registered local segmenter in one batch and return aligned words per note."""
    if not texts:
        return []
    segmenter = segmenter.resolve()
    for relative, expected in SEGMENTER_FILES.items():
        with (segmenter / relative).open("rb") as stream:
            if file_digest(stream, "sha256").hexdigest() != expected:
                raise ValueError("Tệp bộ tách từ không khớp SHA-256 đã ghim.")
    if any(BOUNDARY in text for text in texts):
        raise ValueError("Dấu phân ghi chú đã có trong văn bản nguồn.")
    with TemporaryDirectory(prefix="wseg-", dir=segmenter) as scratch:
        source = Path(scratch) / "input.txt"
        output = Path(scratch) / "output.tsv"
        source.write_text(f"\n{BOUNDARY}\n".join(texts) + "\n", encoding="utf-8", newline="\n")
        try:
            result = run(
                [
                    "java",
                    "-Xmx1g",
                    "-Dfile.encoding=UTF-8",
                    "-jar",
                    JAR,
                    "-fin",
                    str(source),
                    "-fout",
                    str(output),
                    "-annotators",
                    "wseg",
                ],
                cwd=segmenter,
                capture_output=True,
                timeout=300,
                check=False,
            )
        except (OSError, TimeoutExpired):
            raise ValueError("Không chạy được VnCoreNLP cục bộ.") from None
        if result.returncode != 0 or not output.is_file():
            raise ValueError("VnCoreNLP kết thúc mà thiếu đầu ra tách từ.")
        words = _segmented_rows(output.read_text(encoding="utf-8"), len(texts))
    return [_aligned_words(text, row) for text, row in zip(texts, words, strict=True)]
