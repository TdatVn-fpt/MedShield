# apps/api/services/hybrid.py — Combine Vietnamese rule and CRF candidates.
from apps.api.adapters import ner, rules
from apps.api.adapters.vi_names_places import PROPAGATED
from apps.api.schemas import Entity

STRUCTURED = frozenset({"DOB", "PHONE", "ID"})


def priority(entity: Entity) -> int:
    """Rank structured rules first, direct discoveries next and repeats last."""
    if entity.label in STRUCTURED and entity.source == rules.SOURCE:
        return 4
    if entity.source == PROPAGATED:
        return 0
    if entity.source == ner.SOURCE:
        return 3
    return 2 if entity.source == rules.SOURCE else 1


def combine(rule_spans: list[Entity], crf_spans: list[Entity]) -> list[Entity]:
    """Combine all candidates and preserve CRF person/address boundaries until calibrated."""
    return rules.resolve_overlaps(rule_spans + crf_spans, priority)
