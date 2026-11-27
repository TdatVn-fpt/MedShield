# tests/test_i2b2_reader.py — Verify the i2b2 reader with invented XML only.
import io
import json
import subprocess
import sys
import tarfile
from pathlib import Path
from xml.sax.saxutils import quoteattr

import pytest

from ml.i2b2_reader import I2B2Error, I2B2Span, parse_xml, summarize

VALUE = "Nora E\u0301lan"
NOTE = f"🩺\nPatient {VALUE}. Visit 2030-01-05."


def _fixture() -> bytes:
    """Create stand-off XML with a fictional note and both native NAME and DATE labels."""
    start = NOTE.index(VALUE)
    visit = "2030-01-05"
    visit_start = NOTE.index(visit)
    return (
        f"<deIdi2b2><TEXT><![CDATA[{NOTE}]]></TEXT><TAGS>"
        f'<NAME id="mock-1" TYPE="PATIENT" start="{start}" end="{start + len(VALUE)}" '
        f"text={quoteattr(VALUE)} />"
        f'<DATE id="mock-2" TYPE="DATE" start="{visit_start}" '
        f'end="{visit_start + len(visit)}" text="{visit}" />'
        "</TAGS></deIdi2b2>"
    ).encode()


def test_preserves_native_date_and_code_points_from_cdata() -> None:
    """Read half-open offsets with emoji and combining marks without mapping DATE to DOB."""
    record = parse_xml(_fixture())
    start = NOTE.index(VALUE)
    assert record.text == NOTE
    assert record.spans[0] == I2B2Span("NAME", "PATIENT", start, start + len(VALUE))
    date = record.spans[1]
    assert date.category == "DATE" and record.text[date.start : date.end] == "2030-01-05"
    assert VALUE not in repr(record)


@pytest.mark.parametrize(
    ("original", "replacement", "message"),
    [
        (b'start="10"', b'start="99"', "ngoài TEXT"),
        (b'end="20"', b'end="10"', "ngoài TEXT"),
        (b'2030-01-05" />', b'2030-01-06" />', "không khớp"),
        (b"<TAGS>", b"<WRONG>", "XML không hợp lệ"),
    ],
)
def test_rejects_invalid_offsets_text_or_structure(
    original: bytes, replacement: bytes, message: str
) -> None:
    """Malformed XML and unverified annotations must fail without exposing original values."""
    payload = _fixture()
    assert original in payload
    with pytest.raises(I2B2Error, match=message) as error:
        parse_xml(payload.replace(original, replacement))
    assert VALUE not in str(error.value)


def test_rejects_doctype_and_custom_entities() -> None:
    """Disallow external and internal declarations before reading any declared entity."""
    payload = b'<!DOCTYPE doc [<!ENTITY x "fixture-private">]>' + _fixture()
    with pytest.raises(I2B2Error, match="khai báo DTD") as error:
        parse_xml(payload)
    assert "fixture-private" not in str(error.value)


def test_cli_streams_tar_without_extracting_and_emits_only_counts(tmp_path: Path) -> None:
    """Check the shipped CLI against a temporary archive with no local extraction."""
    path = tmp_path / "invented.tar.gz"
    payload = _fixture()
    with tarfile.open(path, "w:gz") as archive:
        member = tarfile.TarInfo("private/mock-42.xml")
        member.size = len(payload)
        archive.addfile(member, io.BytesIO(payload))
    result = subprocess.run(
        [sys.executable, "-X", "utf8", "-m", "ml.i2b2_reader", str(path)],
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "corpus_format": "i2b2_2014_track1_xml",
        "notes": 1,
        "spans": 2,
        "counts_by_native_category": {"DATE": 1, "NAME": 1},
    }
    assert b"mock-42" not in result.stdout and VALUE.encode() not in result.stdout
    assert list(tmp_path.iterdir()) == [path]
    direct = tmp_path / "mock.xml"
    direct.write_bytes(payload)
    assert summarize(direct) == summarize(tmp_path) == json.loads(result.stdout)
