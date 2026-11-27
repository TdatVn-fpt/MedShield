# tests/test_phase_q_hybrid.py — Verify that hybrid keeps low-score CRF and handles rule overlap.
from apps.api.adapters import ner, rules
from apps.api.schemas import Entity, Label
from apps.api.services.hybrid import combine


def _span(start: int, end: int, label: Label, source: str, score: float) -> Entity:
    """Create a synthetic competing span with the requested boundaries and source."""
    return Entity(start=start, end=end, label=label, source=source, score=score)


def test_hybrid_preserves_crf_boundaries_and_prioritizes_contextual_structure() -> None:
    """Do not discard low-score CRF or replace its edges with uncalibrated rules."""
    extended = _span(0, 12, "ADDR", rules.SOURCE, 0.89)
    structured = _span(15, 25, "PHONE", rules.SOURCE, 0.97)
    rule_name = _span(30, 39, "NAME", rules.SOURCE, 0.92)
    crf_name = _span(30, 39, "NAME", ner.SOURCE, 0.4)
    partial_rule = _span(50, 62, "NAME", rules.SOURCE, 0.92)
    partial_crf = _span(55, 64, "NAME", ner.SOURCE, 0.4)
    contained = _span(2, 12, "ADDR", ner.SOURCE, 0.49)
    low_score = _span(40, 45, "ADDR", ner.SOURCE, 0.23)
    unanchored = _span(57, 60, "PHONE", rules.SOURCE + "+phone-standalone", 0.8)
    assert combine(
        [extended, structured, rule_name, partial_rule, unanchored],
        [
            contained,
            _span(13, 20, "NAME", ner.SOURCE, 0.99),
            low_score,
            crf_name,
            partial_crf,
        ],
    ) == [contained, structured, crf_name, low_score, partial_crf]
