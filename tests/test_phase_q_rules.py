# tests/test_phase_q_rules.py — Verify Vietnamese recognizers on independent synthetic fixtures.
import unicodedata

import pytest

from apps.api.adapters import rules
from apps.api.schemas import AnalyzeRequest, Label
from apps.api.services.analysis import analyze_text


def _matches(text: str, label: Label) -> list[tuple[int, int, str]]:
    """_matches extracts spans for label from the original text using the Vietnamese adapter."""
    return [
        (entity.start, entity.end, text[entity.start : entity.end])
        for entity in rules.recognize(text, language="vi")
        if entity.label == label
    ]


def _assert_exact(text: str, label: Label, value: str) -> None:
    """_assert_exact checks a single expected slice and both original code point offsets."""
    start = text.index(value)
    assert _matches(text, label) == [(start, start + len(value), value)]


@pytest.mark.parametrize(
    ("prefix", "value"),
    [
        ("Điện thoại: ", "0321234567"),
        ("SĐT: ", "0392345678"),
        ("Số điện thoại: ", "0523123456"),
        ("Liên hệ: ", "0562345678"),
        ("Điện thoại: ", "0583456789"),
        ("SĐT: ", "0591234567"),
        ("Liên hệ: ", "0701234567"),
        ("SĐT: ", "0762345678"),
        ("Điện thoại: ", "0791234567"),
        ("Số điện thoại: ", "0812345678"),
        ("SĐT: ", "0898345678"),
        ("Điện thoại: ", "0901234567"),
        ("SĐT: ", "0982345678"),
        ("Liên hệ: ", "090.123.4567"),
        ("SĐT: ", "081-234-5678"),
        ("Điện thoại: ", "032 123 4567"),
        ("Liên hệ: ", "+84901234567"),
        ("SĐT: ", "+84 981 234 567"),
        ("Điện thoại: ", "024 3123 4567"),
        ("SĐT: ", "02838234567"),
    ],
)
def test_vietnamese_phone_recognizer(prefix: str, value: str) -> None:
    """Recognize mobile, landline, local and international formatting without punctuation."""
    _assert_exact(f"📞 {prefix}{value}. Hẹn sau.", "PHONE", value)


@pytest.mark.parametrize(
    "text",
    [
        "Số lưu kho: 0900000041.",
        "Kết quả xét nghiệm: 0901234567.",
        "CCCD: 079090123456.",
    ],
)
def test_vietnamese_phone_rejects_nonphone_and_partial_values(text: str) -> None:
    """Reject warehouse and measurement cases and avoid taking pieces of longer numeric IDs."""
    assert _matches(text, "PHONE") == []


@pytest.mark.parametrize("value", ["09012345678", "0123456789", "091234567", "024 1234 5678"])
def test_vietnamese_phone_keeps_explicit_number_outside_allocation(value: str) -> None:
    """Retain the entire labeled contact after the Phase Q2 policy change."""
    _assert_exact(f"Điện thoại: {value}.", "PHONE", value)


@pytest.mark.parametrize(
    ("prefix", "value"),
    [
        ("Sinh ngày ", "03/04/1987"),
        ("Ngày sinh: ", "4/7/1991"),
        ("Ngày sinh: ", "29/02/2000"),
        ("Ngày sinh: ", "1-2-1988"),
        ("DOB: ", "09-12-2002"),
        ("DOB: ", "1993-07-31"),
        ("Ngày sinh: ", "2000-02-29"),
        ("Ngay sinh: ", "21/03/1982"),
        ("Ngày sinh: ", "12.08.1994"),
        ("SN: ", "14.9.1997"),
        ("SN: ", "31/12/99"),
        ("Ngày sinh: ", "9-1-07"),
        ("Năm sinh ", "1978"),
        ("Sinh năm ", "1995"),
        ("nam sinh: ", "1983"),
        ("Năm sinh: ", "2003"),
        ("SN: ", "2004"),
        ("Ngày sinh: ", "ngày 5 tháng 3 năm 1990"),
        ("Ngày sinh: ", "ngày 29 tháng 2 năm 2012"),
        ("Ngày sinh: ", "ngay 1 thang 12 nam 1999"),
    ],
)
def test_vietnamese_birthdate_recognizer(prefix: str, value: str) -> None:
    """Recognize calendar dates or birth years by context, preserving the input form."""
    _assert_exact(f"🙂 {prefix}{value}; ngày tái khám 24/11/2026.", "DOB", value)


@pytest.mark.parametrize(
    "text",
    [
        "Ngày tái khám: 12/08/2026.",
        "Tuổi: 29 tuổi.",
    ],
)
def test_vietnamese_birthdate_rejects_administrative_date(text: str) -> None:
    """Keep appointment dates and ages outside the DOB category."""
    assert _matches(text, "DOB") == []


@pytest.mark.parametrize(
    "value",
    ["29/02/1900", "31/02/1998", "1997-06-31", "ngày 31 tháng 4 năm 1996", "1994-13-14"],
)
def test_vietnamese_birthdate_keeps_explicit_impossible_date(value: str) -> None:
    """Keep a clearly labeled birth date even when its calendar fields are inconsistent."""
    _assert_exact(f"Ngày sinh: {value}.", "DOB", value)


@pytest.mark.parametrize(
    ("prefix", "value"),
    [
        ("CCCD: ", "001089123456"),
        ("CCCD: ", "079192123456"),
        ("CCCD: ", "001200234567"),
        ("CCCD: ", "079308234567"),
        ("CMND: ", "123456789"),
        ("CMND: ", "023456789"),
        ("Hộ chiếu: ", "A1234567"),
        ("Hộ chiếu: ", "B12345678"),
        ("Mã BN: ", "BN-01234"),
        ("Mã BN: ", "001234"),
        ("Mã HS: ", "HS-4321"),
        ("Mã HS: ", "AB-98765"),
        ("Mã bệnh nhân: ", "BN-30201"),
        ("Mã bệnh án: ", "HS-70352"),
        ("Mã hồ sơ: ", "MA-3012"),
        ("Số hồ sơ: ", "765432"),
        ("Số HSBA: ", "BA-4031"),
        ("PID: ", "PT-6972"),
        ("Ma BN: ", "BN-5721"),
        ("Mã ", "BN-1901"),
    ],
)
def test_vietnamese_id_recognizer(prefix: str, value: str) -> None:
    """Recognize context-bound personal and patient IDs without swallowing ICD codes."""
    _assert_exact(f"📋 {prefix}{value}; mã ICD J06.9.", "ID", value)


@pytest.mark.parametrize(
    "text",
    [
        "Mã phòng: BN-4101.",
        "Mã thuốc: HS-4203.",
    ],
)
def test_vietnamese_id_rejects_wrong_context(text: str) -> None:
    """Reject patient-shaped codes in a room or medication field."""
    assert _matches(text, "ID") == []


@pytest.mark.parametrize(
    ("cue", "value"),
    [
        ("CCCD: ", "999089123456"),
        ("CCCD: ", "07908912345"),
        ("CMND: ", "1234567899"),
        ("CCCD: ", "0790891234567"),
        ("Sinh năm 1992; CCCD: ", "001089123456"),
    ],
)
def test_vietnamese_id_keeps_explicit_unusual_identifier(cue: str, value: str) -> None:
    """Keep the complete labeled ID even when allocation or cross-field validation fails."""
    _assert_exact(f"{cue}{value}.", "ID", value)


@pytest.mark.parametrize(
    ("prefix", "value"),
    [
        ("Bệnh nhân: ", "Nguyễn Minh An"),
        ("BN: ", "Nguyễn Minh Lan"),
        ("Họ tên: ", "Võ Hải Phong"),
        ("Người bệnh ", "Mai An"),
        ("Bác sĩ ", "Trần Văn Bình"),
        ("BS. ", "Lê Bảo Ngọc"),
        ("Người thân: ", "Phạm Hải Minh"),
        ("Người liên hệ: ", "Hoàng Lâm Anh"),
        ("Bệnh nhân: ", "nguyễn minh hà"),
        ("BN: ", "nguyen minh anh"),
        ("Ho ten: ", "vo hai dang"),
        ("Bac si ", "tran bao an"),
        ("Bệnh nhân: ", "NGUYỄN ANH KHOA"),
        ("Họ tên: ", "Đặng An Nhiên"),
        ("Bệnh nhân: ", "Đinh Thùy Dương"),
        ("Người bệnh ", "Lý Khánh Linh"),
        ("Người thân: ", "Bùi Anh Tâm"),
        ("Bệnh nhân: ", "Dương Văn Thành"),
        ("Họ tên: ", "Hồ Hải An"),
        ("Họ tên: ", unicodedata.normalize("NFD", "Nguyễn Gia Bảo")),
    ],
)
def test_vietnamese_name_recognizer(prefix: str, value: str) -> None:
    """Recognize contextual names across capitalization/accent forms and preserve marks."""
    _assert_exact(f"🙂 {prefix}{value}, khám vì đau nhẹ.", "NAME", value)


def test_vietnamese_name_does_not_treat_place_as_person() -> None:
    """Keep the location from a clinical statement outside the person's span."""
    _assert_exact("BN: Đặng Minh An đến khám ở Bệnh viện Hoa Sen.", "NAME", "Đặng Minh An")


@pytest.mark.parametrize(
    ("prefix", "value"),
    [
        ("Địa chỉ: ", "12 đường Sen, phường Bình An, TP. Thủ Đức"),
        ("Địa chỉ cư trú: ", "25 đường Huệ, quận 1, TP. Hồ Chí Minh"),
        ("Địa chỉ: ", "4 ngõ Hoa Ban, phường Vân Phúc, Hà Nội"),
        ("Đ/c: ", "19/7 đường Mây, P. Minh Quang"),
        ("D/c: ", "31 duong Dao, P. An Lam"),
        ("Địa chỉ: ", "55-57 đường Sậy, phường Thạch An"),
        ("Địa chỉ: ", "tổ 2, khu phố Vườn Tre"),
        ("Thường trú: ", "thôn Tre, xã Đông Lâm"),
        ("Quê quán: ", "ấp Sen, xã Nam Thiên"),
        ("HKTT: ", "số nhà 77, đường Mộc, tỉnh Đồng Nai"),
        ("Dia chi: ", "29 duong Tra, Ha Noi"),
        ("Địa chỉ: ", "25 đường Trúc, P. 9, Q. 4"),
        ("Cư trú: ", "21 đường Dừa, Đà Nẵng"),
        ("Nơi ở: ", "72 đường Sứ, Hải Phòng"),
        ("Địa chỉ: ", "98 phố Lục Bình, Cần Thơ"),
        ("Địa chỉ: ", "18 đường Cỏ May, Bình Định"),
        ("Địa chỉ: ", "25 đường Hải Đăng, Quy Nhơn"),
        ("Địa chỉ: ", "38 đường Bàng, T. An Giang"),
        ("Địa chỉ: ", "42 đường Nắng, tỉnh Lâm Đồng"),
        ("Địa chỉ: ", unicodedata.normalize("NFD", "7 phố Sen, Hà Nội")),
    ],
)
def test_vietnamese_address_recognizer(prefix: str, value: str) -> None:
    """Keep address separators and abbreviations inside the original contextual span."""
    _assert_exact(f"🙂 {prefix}{value}. Hẹn tái khám ngày mai.", "ADDR", value)


def test_vietnamese_address_does_not_treat_clinic_as_residence() -> None:
    """A care location with a recognizable place name is not a residential address."""
    assert _matches("Khám tại Bệnh viện Hoa Sen, Hà Nội.", "ADDR") == []


def test_following_exact_name_repeat_gets_distinct_source_and_reused_token() -> None:
    """Only repeats after the high-confidence anchor qualify, and case variants stay intact."""
    text = (
        "Lê Thiên An được ghi ở đầu mục. Bệnh nhân: Lê Thiên An. "
        "Hôm nay Lê Thiên An nghỉ. Hồ sơ ghi lê thiên an."
    )
    result = analyze_text(AnalyzeRequest(text=text, language="vi", mode="rules"))
    names = [entity for entity in result.entities if entity.label == "NAME"]
    assert len(names) == 2
    assert all(text[entity.start : entity.end] == "Lê Thiên An" for entity in names)
    assert names[0].start == text.index("Lê Thiên An", text.index("Bệnh nhân"))
    assert names[1].source != names[0].source
    assert result.redacted_text.count("[NAME_1]") == 2
    assert result.redacted_text.startswith("Lê Thiên An được ghi")
    assert result.redacted_text.endswith("Hồ sơ ghi lê thiên an.")
