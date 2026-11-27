# ml/i2b2_reader.py — Parse local 2014 i2b2 XML and report only aggregate structure.
import json
import re
import tarfile
from argparse import ArgumentParser
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import IO
from xml.etree import ElementTree

MAX_XML_BYTES = 8 * 1024 * 1024
CATEGORIES = frozenset({"NAME", "PROFESSION", "LOCATION", "AGE", "DATE", "CONTACT", "ID"})
SUBTYPE = re.compile(r"[A-Z][A-Z0-9_ -]{0,39}")
OFFSET = re.compile(r"[0-9]{1,8}")


class I2B2Error(ValueError):
    """Signal an invalid input without rendering restricted text, identifiers or paths."""


class _NoDTD(ElementTree.TreeBuilder):
    """Prevent DTD and declared entity processing; i2b2 documents do not require them."""

    def doctype(self, name: str, pubid: str | None, system: str | None) -> None:
        """Reject a DTD without printing its identifiers or source location."""
        raise I2B2Error("XML có khai báo DTD.")


@dataclass(frozen=True, slots=True)
class I2B2Span:
    """Store the native category, subtype and half-open code point interval."""

    category: str
    subtype: str
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class I2B2Record:
    """Store one native document in memory and omit text from its repr."""

    text: str = field(repr=False)
    spans: tuple[I2B2Span, ...]


def _span(element: ElementTree.Element, text: str) -> I2B2Span:
    """Validate the published native label and verify offsets against the parsed document."""
    subtype = element.get("TYPE", "")
    raw_start, raw_end = element.get("start", ""), element.get("end", "")
    if (
        element.tag not in CATEGORIES
        or not SUBTYPE.fullmatch(subtype)
        or len(element)
        or not OFFSET.fullmatch(raw_start)
        or not OFFSET.fullmatch(raw_end)
    ):
        raise I2B2Error("Một thẻ PHI thiếu loại hoặc offset số hợp lệ.")
    start, end = int(raw_start), int(raw_end)
    if not (0 <= start < end <= len(text)):
        raise I2B2Error("Biên thẻ nằm ngoài TEXT hoặc rỗng.")
    value = text[start:end]
    if not value.strip() or element.get("text") != value:
        raise I2B2Error("Giá trị của thẻ không khớp biên trên TEXT.")
    return I2B2Span(element.tag, subtype, start, end)


def parse_xml(payload: bytes) -> I2B2Record:
    """Read one UTF-8 stand-off XML note without projecting i2b2 tags onto MedShield labels."""
    if len(payload) > MAX_XML_BYTES:
        raise I2B2Error("Tệp XML vượt giới hạn 8 MiB.")
    try:
        root = ElementTree.fromstring(
            payload.decode("utf-8-sig"), parser=ElementTree.XMLParser(target=_NoDTD())
        )
    except (ElementTree.ParseError, UnicodeError):
        raise I2B2Error("XML không hợp lệ hoặc không dùng UTF-8.") from None
    text_nodes, tag_nodes = root.findall("TEXT"), root.findall("TAGS")
    if len(text_nodes) != 1 or len(tag_nodes) != 1 or len(text_nodes[0]):
        raise I2B2Error("Cần đúng một TEXT dạng văn bản và một TAGS dạng stand-off.")
    text = text_nodes[0].text or ""
    if not text.strip():
        raise I2B2Error("TEXT rỗng.")
    return I2B2Record(text, tuple(_span(element, text) for element in tag_nodes[0]))


def _read_xml(stream: IO[bytes]) -> bytes:
    """Read at most one bounded XML member; parser checks for an over-limit sentinel."""
    return stream.read(MAX_XML_BYTES + 1)


def _documents(source: Path) -> Iterator[bytes]:
    """Yield XML bytes from a file, local directory or tar.gz without extracting any archive."""
    if source.is_dir():
        root = source.resolve(strict=True)
        for path in sorted(root.rglob("*.xml")):
            if path.is_symlink() or not path.resolve(strict=True).is_relative_to(root):
                raise I2B2Error("Thư mục chứa liên kết XML ngoài phạm vi đã chọn.")
            if path.is_file():
                with path.open("rb") as stream:
                    yield _read_xml(stream)
        return
    if source.suffix.casefold() == ".xml":
        with source.open("rb") as stream:
            yield _read_xml(stream)
        return
    if not source.name.lower().endswith((".tar.gz", ".tgz")):
        raise I2B2Error("Cần tệp XML, thư mục XML hoặc archive tar.gz cục bộ.")
    with tarfile.open(source, mode="r|gz") as archive:
        for member in archive:
            name = PurePosixPath(member.name)
            if name.suffix.lower() != ".xml":
                continue
            if not member.isfile() or member.size > MAX_XML_BYTES:
                raise I2B2Error("Một thành viên XML trong archive không phải tệp hợp lệ.")
            entry = archive.extractfile(member)
            if entry is None:
                raise I2B2Error("Không đọc được thành viên XML trong archive.")
            with entry:
                yield _read_xml(entry)


def summarize(source: Path) -> dict[str, object]:
    """Return only fixed category names and counts, with no text, offsets or identifiers."""
    counts: Counter[str] = Counter()
    notes = 0
    for payload in _documents(source):
        record = parse_xml(payload)
        notes += 1
        counts.update(span.category for span in record.spans)
    if not notes:
        raise I2B2Error("Không tìm thấy bản ghi XML.")
    return {
        "corpus_format": "i2b2_2014_track1_xml",
        "notes": notes,
        "spans": counts.total(),
        "counts_by_native_category": dict(sorted(counts.items())),
    }


def main() -> None:
    """Check an approved local source and print a sanitized aggregate to stdout."""
    parser = ArgumentParser(description="Kiểm tra cấu trúc XML i2b2 2014 theo nhóm gốc.")
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    try:
        result = summarize(args.source)
    except I2B2Error as exc:
        parser.exit(1, f"i2b2: {exc}\n")
    except (OSError, EOFError, tarfile.TarError):
        parser.exit(1, "i2b2: Nguồn không đọc được hoặc archive không hợp lệ.\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
