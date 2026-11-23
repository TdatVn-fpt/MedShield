# apps/api/services/redaction.py — Validate reviewed spans and replace them consistently.
from apps.api.schemas import LABELS, Entity, Metadata, RedactResponse


class InvalidSpanError(Exception):
    """InvalidSpanError signals an invalid boundary/overlap without retaining input."""


def validate_spans(text: str, entities: list[Entity]) -> list[Entity]:
    """validate_spans returns ordered, disjoint codepoint spans or raises a safe error.

    Python indices already count Unicode codepoints, including combining marks.
    Adjacent spans are valid; duplicate or partially intersecting spans are rejected.
    """
    ordered = sorted(entities, key=lambda entity: (entity.start, entity.end))
    previous_end = 0
    for entity in ordered:
        if not 0 <= entity.start < entity.end <= len(text) or entity.start < previous_end:
            raise InvalidSpanError
        previous_end = entity.end
    return ordered


def redact_text(text: str, entities: list[Entity]) -> RedactResponse:
    """redact_text replaces exact (label, original slice) matches with shared tokens.

    Each call starts fresh numbering per label. Original strings exist only in this
    function's local token map and are never returned, persisted or logged.
    """
    ordered = validate_spans(text, entities)
    counts = dict.fromkeys(LABELS, 0)
    unique_counts = dict.fromkeys(LABELS, 0)
    tokens: dict[tuple[str, str], str] = {}
    parts: list[str] = []
    cursor = 0
    for entity in ordered:
        key = (entity.label, text[entity.start : entity.end])
        if key not in tokens:
            unique_counts[entity.label] += 1
            tokens[key] = f"[{entity.label}_{unique_counts[entity.label]}]"
        parts.extend((text[cursor : entity.start], tokens[key]))
        cursor = entity.end
        counts[entity.label] += 1
    parts.append(text[cursor:])
    return RedactResponse(
        redacted_text="".join(parts),
        metadata=Metadata(entity_count=len(ordered), counts_by_label=counts),
    )
