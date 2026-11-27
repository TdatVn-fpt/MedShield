# apps/api/adapters/vi_boundaries.py — Trim external field separators without changing source text.
from apps.api.schemas import Entity

FIELD_SEPARATORS = frozenset(",;|:")


def refine(text: str, entities: list[Entity]) -> list[Entity]:
    """Trim only outer field delimiters and whitespace, keeping internal separators and marks."""
    result = []
    for entity in entities:
        start, end = entity.start, entity.end
        while start < end and (text[start].isspace() or text[start] in FIELD_SEPARATORS):
            start += 1
        while end > start and (text[end - 1].isspace() or text[end - 1] in FIELD_SEPARATORS):
            end -= 1
        if start < end:
            result.append(entity.model_copy(update={"start": start, "end": end}))
    return result
