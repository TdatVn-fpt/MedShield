# tests/test_phase_q2_structured.py — Exercise contextual and standalone structured rules.
from datetime import date

import pytest

from apps.api.adapters import rules
from apps.api.adapters.vi_structured import (
    PHONE_REVIEW_SOURCE,
    SOURCE,
    STANDALONE_PHONE_SOURCE,
    structured_candidates,
)
from apps.api.schemas import Entity, Label


def _values(text: str, label: Label) -> list[tuple[str, Entity]]:
    """Return slices and entities in original coordinate order for one label."""
    return [
        (text[item.start : item.end], item)
        for item in rules.recognize(text, "vi")
        if item.label == label
    ]


def test_contact_context_preserves_inventory_and_measurements() -> None:
    """A contact number must not carry over to a closer inventory or measurement cue."""
    text = (
        "Điện thoại người giám hộ: 0061 72 0083, vật tư số lô 0980609012; "
        "chỉ số xét nghiệm: 0898317829. Nhắn tin tới Zalo: 0039-20-8730."
    )
    phones = _values(text, "PHONE")
    assert [(value, item.source) for value, item in phones] == [
        ("0061 72 0083", SOURCE),
        ("0039-20-8730", SOURCE),
    ]
    assert all(text.index(value) == item.start for value, item in phones)


def test_contact_block_and_marked_extension_are_contact_fields() -> None:
    """Recognize an out-of-plan number and a labeled extension in a contact block."""
    text = "Chi tiết liên hệ:\r\n  - 707 210 49 ext. 716. Khám lại ngày 19/04."
    assert [value for value, _ in _values(text, "PHONE")] == ["707 210 49", "716"]


def test_parenthesized_area_code_is_not_split() -> None:
    """Treat the area code and subscriber number in one labeled landline as one span."""
    assert [value for value, _ in _values("Hotline: (024) 3677 4215.", "PHONE")] == [
        "(024) 3677 4215"
    ]


@pytest.mark.parametrize(
    ("cue", "value"),
    [
        ("Máy lẻ liên hệ: ", "13-24-57"),
        ("Hotline: ", "15-26-91"),
        ("ĐT. cá nhân: ", "719 398"),
    ],
)
def test_explicit_contact_wins_over_shape_and_accepts_abbreviation(cue: str, value: str) -> None:
    """Retain short date-shaped contact values even after a dotted field abbreviation."""
    assert [actual for actual, _ in _values(f"{cue}{value}.", "PHONE")] == [value]


def test_long_phone_like_span_never_clips_first_part() -> None:
    """An unmarked trailing group is retained only as part of an explicit contact."""
    value = "096 200 3317 82"
    assert _values(f"Dãy tham chiếu {value}.", "PHONE") == []
    assert [v for v, _ in _values(f"Điện thoại: {value}.", "PHONE")] == [value]


def test_standalone_structural_signals_are_additive() -> None:
    """A plausible-looking shape with no length or allocation signals remains a review item."""
    text = "Phiếu đối chiếu 000 830 7124. Dãy rời 097 600 9173. Dòng cuối +84 891 251 661 22."
    phones = _values(text, "PHONE")
    assert [(value, item.source, item.score) for value, item in phones] == [
        ("000 830 7124", STANDALONE_PHONE_SOURCE, 0.6),
        ("097 600 9173", STANDALONE_PHONE_SOURCE, 0.8),
        ("+84 891 251 661 22", PHONE_REVIEW_SOURCE, 0.4),
    ]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "Sửa ngày sinh trên thẻ từ 09.08.1976 thành 09.08.1978. Hẹn 20.08.2026.",
            ["09.08.1976", "09.08.1978"],
        ),
        ("Năm sinh của người giám hộ trên phiếu là 1964.", ["1964"]),
        ("Sinh ngày 2 tháng 7 năm 2001.", ["ngày 2 tháng 7 năm 2001"]),
        ("Học sinh 1996 có lịch khám.", []),
        ("Học sinh năm 2020 được khám định kỳ.", []),
        ("Ngày sinh: 07-04/1998.", []),
        ("Ngày sinh chưa rõ; tái khám ngày 04/06/2026.", []),
        ("Ngày sinh chưa rõ ngày nhập viện 10/08/2026.", []),
    ],
)
def test_birth_date_context_and_correction_boundaries(text: str, expected: list[str]) -> None:
    """Recover both corrected values and reject wrong cues or mixed date separators."""
    assert [value for value, _ in _values(text, "DOB")] == expected


def test_validation_adds_confidence_without_veto() -> None:
    """A calendar or ID anomaly lowers corroboration and retains the contextual span."""
    text = "ngay sinh: 01/02/1981. ngay sinh: 31/02/1981. cccd: 001081702111. cccd: 988081702112."
    items = list(structured_candidates(text, date(2026, 11, 25)))
    assert [(text[e.start : e.end], e.label, e.score) for e in items] == [
        ("01/02/1981", "DOB", 0.97),
        ("31/02/1981", "DOB", 0.84),
        ("001081702111", "ID", 0.97),
        ("988081702112", "ID", 0.81),
    ]
