# tests/test_meddies_mapping_rules.py — Check reviewed train spans and original code-point offsets.
from collections import Counter
from typing import Any

import pytest

from ml.meddies_mapping_rules import remap_entities


def _entity(text: str, value: str, label: str) -> dict[str, Any]:
    """Create a publisher span over the first occurrence of an invented value."""
    start = text.index(value)
    return {"start": start, "end": start + len(value), "label": label}


@pytest.mark.parametrize(
    ("text", "label", "value", "expected", "rules"),
    [
        (
            "🙂 Người kê: PGS.TS. Bác sĩ : Lê Thảo An",
            "NAME",
            "PGS.TS. Bác sĩ : Lê Thảo An",
            "Lê Thảo An",
            {"name_title_trimmed": 1},
        ),
        (
            "Bác sĩ:\u00a0\u2009Lê Thảo An",
            "NAME",
            "Bác sĩ:\u00a0\u2009Lê Thảo An",
            "Lê Thảo An",
            {"name_title_trimmed": 1},
        ),
        ("Người kê: BS.", "NAME", "BS.", None, {"name_title_only_removed": 1}),
        ("Họ và tên: Anh Thư", "NAME", "Anh Thư", "Anh Thư", {}),
        ("Người gọi: Ba Đình", "NAME", "Ba Đình", "Ba Đình", {}),
        (
            "Người gọi: Anh Nguyễn Mộc An",
            "NAME",
            "Anh Nguyễn Mộc An",
            "Nguyễn Mộc An",
            {"name_title_trimmed": 1},
        ),
        ("Người gọi: Bà An", "NAME", "Bà An", "An", {"name_title_trimmed": 1}),
        (
            "Phòng khám Thử Nghiệm\nKhoa Nhi\nTầng 8, 12 phố Hoa Nắng",
            "ADDR",
            "Tầng 8, 12 phố Hoa Nắng",
            None,
            {"addr_facility_removed": 1},
        ),
        (
            "Đơn vị｜Phòng khám Thử Nghiệm\nĐịa chỉ liên hệ｜18 phố Mưa Phùn",
            "ADDR",
            "18 phố Mưa Phùn",
            None,
            {"addr_facility_removed": 1},
        ),
        (
            "Bệnh viện Hoa Nắng\nĐịa chỉ nhà của bệnh nhân: 13 phố Mầm Trăng",
            "ADDR",
            "13 phố Mầm Trăng",
            "13 phố Mầm Trăng",
            {},
        ),
        (
            "Kết nối [2001:db8::742]:4242",
            "ADDR",
            "[2001:db8::742]:4242",
            None,
            {"addr_ip_removed": 1},
        ),
        (
            '"prescriptionId": "RX-XIEC-001"',
            "ID",
            "RX-XIEC-001",
            None,
            {"id_document_code_removed": 1},
        ),
        (
            "**Mã phiếu khám**: PK-XIEC-001",
            "ID",
            "PK-XIEC-001",
            None,
            {"id_document_code_removed": 1},
        ),
        (
            "OBR|1|REQ-CHIMSAO|REQ-XIEC|",
            "ID",
            "REQ-CHIMSAO",
            None,
            {"id_document_code_removed": 1},
        ),
        ("PID|1||BN-CHIMSAO|", "ID", "BN-CHIMSAO", "BN-CHIMSAO", {}),
        (
            "OBX|1|NM|Mau|1|201|mg/dL|141-180|H",
            "ID",
            "141-180",
            None,
            {"id_lab_reference_removed": 1},
        ),
        ("Mã bệnh án: 141-180", "ID", "141-180", "141-180", {}),
        (
            "Mã thiết bị: DEV-XIEC-001",
            "ID",
            "DEV-XIEC-001",
            None,
            {"id_non_person_code_removed": 1},
        ),
        (
            "🙂 Mã số bảo hiểm: BHYT–45-678",
            "ID",
            "Mã số bảo hiểm: BHYT–45-678",
            "45-678",
            {"id_field_trimmed": 1, "id_bhyt_anchor_trimmed": 1},
        ),
        (
            "Mã bệnh nhân:\u202fBN-RAU-01",
            "ID",
            "Mã bệnh nhân:\u202fBN-RAU-01",
            "BN-RAU-01",
            {"id_field_trimmed": 1},
        ),
        ("Số thẻ: BH-45678", "ID", "BH-45678", "BH-45678", {}),
    ],
)
def test_reviewed_rules(
    text: str, label: str, value: str, expected: str | None, rules: dict[str, int]
) -> None:
    """Verify action counts and exact original substrings for each reviewed rule."""
    corrections: Counter[str] = Counter()
    spans = remap_entities(text, [_entity(text, value, label)], corrections)
    assert spans == ([] if expected is None else [_entity(text, expected, label)])
    assert dict(corrections) == rules


def test_unrevised_dob_and_phone_retain_both_offsets() -> None:
    """Keep DOB and PHONE unchanged beside a removed document ID and a trimmed name."""
    text = "🙂 BS. Nguyễn Bình\nMã đơn: DT-001\nDOB 1988\nLiên hệ: 000.000.0022"
    protected = [_entity(text, "1988", "DOB"), _entity(text, "000.000.0022", "PHONE")]
    original = [
        _entity(text, "BS. Nguyễn Bình", "NAME"),
        _entity(text, "DT-001", "ID"),
        *protected,
    ]
    assert remap_entities(text, original, Counter()) == [
        _entity(text, "Nguyễn Bình", "NAME"),
        *protected,
    ]
