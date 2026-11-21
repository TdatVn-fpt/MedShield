# apps/api/adapters/rules.py — Context-sensitive baseline recognizers for synthetic notes.
import re
from collections.abc import Iterator

from apps.api.schemas import Entity, Label

SOURCE = "medshield-rules"
NAME_PREFIX = (
    r"(?:người bệnh|bệnh nhân|họ tên|bác sĩ|người liên hệ|người thân|BN|BS\.?|patient|Dr\.?)"
)
NAME_STOP = r"(?=\s*(?:[,;:\n\r.!?]|$|\bsinh\b|\btái khám\b|\bđến khám\b|\bkhám vì\b|\bđược\b))"
PATTERNS: tuple[tuple[Label, str, float], ...] = (
    (
        "DOB",
        r"(?:sinh ngày|ngày sinh|năm sinh|DOB|born|date of birth)\s*[:\-]?\s*"
        r"(?P<value>\d{1,2}[/.-]\d{1,2}[/.-]\d{4}|\d{4})\b",
        0.96,
    ),
    ("ID", r"(?P<value>\b(?:BN|HS|MRN)[-\s]?\d{3,12}\b)", 0.95),
    (
        "ID",
        r"(?:CCCD|CMND|hộ chiếu|mã bệnh nhân|mã bệnh án|mã hồ sơ|MRN)\s*[:\-]?\s*"
        r"(?P<value>[A-Z0-9][A-Z0-9-]{3,19})\b",
        0.95,
    ),
    (
        "PHONE",
        r"(?:điện thoại|số điện thoại|liên hệ|SĐT|phone|tel)\s*[:\-]?\s*"
        r"(?P<value>\+?\d[\d .()-]{7,19}\d)",
        0.94,
    ),
    ("PHONE", r"(?<!\w)(?P<value>(?:\+84|0)[35789]\d{8})(?!\w)", 0.9),
    ("NAME", NAME_PREFIX + r"\s*[:\-]?\s+(?P<value>[^\d,;:\n\r.!?]{2,70}?)" + NAME_STOP, 0.8),
)


def _addresses(text: str) -> Iterator[Entity]:
    """_addresses keeps internal commas/TP. abbreviations but stops at a new field/sentence."""
    prefix = re.compile(r"(?:địa chỉ|cư trú|nơi ở|address)\s*[:\-]?\s*", re.IGNORECASE)
    ending = re.compile(
        r";|\r?\n(?=\s*(?:SĐT|Điện thoại|Hẹn|Chẩn đoán|Mã))|"
        r"(?<!TP)(?<!Tp)(?<!tp)(?<!P)(?<!Q)\.(?:\s|$)|$"
    )
    for match in prefix.finditer(text):
        tail = text[match.end() :]
        stop = ending.search(tail)
        if stop is None:
            continue
        value = tail[: stop.start()].rstrip()
        if value and len(value) <= 250:
            yield Entity(
                start=match.end(),
                end=match.end() + len(value),
                label="ADDR",
                source=SOURCE,
                score=0.82,
            )


def resolve_overlaps(entities: list[Entity]) -> list[Entity]:
    """resolve_overlaps keeps higher-score spans then longer spans, ordered by position.

    Exact duplicates retain their strongest score. Each candidate is compared with
    accepted spans, so nested/partial overlaps cannot leak into the API contract.
    """
    accepted: list[Entity] = []
    for entity in sorted(entities, key=lambda item: (-item.score, -(item.end - item.start))):
        if not any(entity.start < old.end and old.start < entity.end for old in accepted):
            accepted.append(entity)
    return sorted(accepted, key=lambda item: (item.start, item.end))


def recognize(text: str) -> list[Entity]:
    """recognize returns nonblank, disjoint baseline spans on the unchanged original text."""
    found: list[Entity] = []
    for label, pattern, score in PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            start, end = match.span("value")
            while end > start and text[end - 1].isspace():
                end -= 1
            if end == start:
                continue
            found.append(Entity(start=start, end=end, label=label, source=SOURCE, score=score))
    found.extend(_addresses(text))
    return resolve_overlaps(found)
