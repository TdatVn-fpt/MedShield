# tests/test_phase_q2_boundaries.py — Exercise boundary trimming on untouched Unicode text.
from unicodedata import normalize

from apps.api.adapters import rules
from apps.api.adapters.vi_boundaries import refine
from apps.api.schemas import Entity


def test_vietnamese_cues_leave_phone_transition_and_column_separators_outside() -> None:
    """Use a development form with lowercase NFD text and two field delimiter styles."""
    name = normalize("NFD", "lê thanh thảo")
    address = normalize("NFD", "18 ngách Vườn Bàng, P. Nắng Mai")
    note = f"📋 Họ tên: {name} qua số liên hệ; Địa chỉ in trong hồ sơ: {address}, | Mục kế."
    result = [
        (entity.label, note[entity.start : entity.end])
        for entity in rules.vietnamese_candidates(note)
    ]
    assert ("NAME", name) in result
    assert ("ADDR", address) in result


def test_refinement_keeps_internal_punctuation_and_combining_mark() -> None:
    """Trim delimiters around a candidate while preserving the internal punctuation verbatim."""
    value = normalize("NFD", "Xã Hoa Cẩm, Q. Bắc Đảo")
    text = f"🔎 | {value}, |"
    span = Entity(start=2, end=len(text), label="ADDR", source="medshield-crf", score=0.45)
    [result] = refine(text, [span])
    assert result.start == 4
    assert text[result.start : result.end] == value
    assert result.source == span.source and result.score == span.score
