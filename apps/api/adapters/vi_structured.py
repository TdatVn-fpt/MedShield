# apps/api/adapters/vi_structured.py — Validate Vietnamese dates, telephone numbers and IDs.
import re
from collections.abc import Iterator
from datetime import date

import phonenumbers

from apps.api.schemas import Entity

SOURCE = "medshield-rules"
STANDALONE_PHONE_SOURCE = "medshield-rules+phone-standalone"
PHONE_REVIEW_SOURCE = "medshield-rules+phone-review"
SEP = r"[ \t]*[:=–-]?[ \t]*"
DOB_CUE = re.compile(
    r"\b(?:sinh(?=[ \t]+ngay[ \t]+[0-9]{1,2}[ \t]+thang\b)|"
    r"sinh[ \t]+(?:ngay|nam)|(?:ngay|nam)[ \t]+sinh|dob|sn)\b"
)
DATE_VALUE = re.compile(
    r"(?<!\w)(?<![0-9][/.-])(?:"
    r"(?:ngay[ \t]+)?[0-9]{1,2}[ \t]+thang[ \t]+[0-9]{1,2}[ \t]+nam[ \t]+[0-9]{4}|"
    r"[0-9]{4}[/.-][0-9]{1,2}[/.-][0-9]{1,2}|"
    r"[0-9]{1,2}[/.-][0-9]{1,2}[/.-][0-9]{2,4}|[0-9]{4})(?!\w|[/.-][0-9])"
)
OTHER_DATE_FIELD = re.compile(
    r"\b(?:hen|tai kham|ngay (?:kham|nhap|xuat|lap|cap|nhan|tao)|"
    r"tuoi|cccd|cmnd|ma ho so|sdt|dien thoai)\b"
)
DATE_GAP = re.compile(r"[ \t:=–-]*(?:[a-z]+[ \t:=–-]+){0,10}")
DATE_CORRECTION = re.compile(r"[ \t,–-]*(?:(?:sua|doi|chinh|chuyen|ghi) +)?(?:thanh|sang)\b")
PHONE_RUN = re.compile(
    r"(?<![\w+])(?<![0-9][/.-])(?:\((?:\+[0-9]{1,3}|0[0-9]{1,3})\)[ .\t-]?|\+)?"
    r"[0-9]+(?:[ .\t-]+[0-9]+)*(?!\w|[/.-][0-9])"
)
PHONE_SEPARATOR = re.compile(r"(?<=[0-9]{9})[ \t]+(?=0[0-9]{9,10}(?![0-9]))")
PHONE_EXT = re.compile(r"\b(?:may le|so nhanh|so noi bo|ext\.?)[ \t:=]*$")
PHONE_EXT_SHORT = re.compile(r"\bx[ \t:=]*$")
STANDALONE_PHONE = re.compile(r"(?:0(?:2[0-9]{9}|[0-9]{9})|\+[1-9][0-9]{8,13})$")
PHONE_LOCATOR = re.compile(
    r"\b(?:sdt|dt|dien thoai|lien he|lien lac|hotline|tel|phone|zalo|"
    r"so (?:may|rieng|lien lac|di dong|dang dung|nhan tin)|"
    r"may cua|di dong|(?:goi(?: lai)?|nhan tin)(?=[ \t]+(?:bang|qua|toi|den|so|lai)\b)|"
    r"(?:theo|qua|bang) so)\b"
)
PHONE_CUE = re.compile(PHONE_LOCATOR.pattern + r"(?:[^;|,\r\n:!?]|:(?=[ \t]*$)){0,64}[:= \t-]*$")
NON_PHONE = re.compile(
    r"\b(?:kho|luu kho|ma|cccd|cmnd|icd|mau|gia|tien|vien phi|vat tu|"
    r"giao dich|nong do|chi so|xet nghiem|giuong|phong|lieu|can nang|so lo|"
    r"mmhg|spo2|nhiet do|mach|huyet ap|tai kham|ngay kham|ngay sinh|nam sinh)\b"
)
CONTACT_BLOCK = re.compile(r"(?:^|\n)[ \t]*(?:thong tin|chi tiet)?[ \t]*(?:lien he|lien lac)\b")
CONTACT_FIELD_END = re.compile(r"[;|,\r\n!?]|(?<!\bdt)(?<!\bsdt)\.")
ID = re.compile(
    r"\b(?P<cue>cccd|cmnd|can cuoc(?: cong dan)?|chung minh nhan dan|"
    r"ho chieu|(?:the |so )?bhyt|pid|mrn|(?:ma|so) "
    r"(?:bn|hsba|hs|benh nhan|benh an|ho so)(?=[ \t:=])"
    r"|(?:ma|ho so|benh an)(?=[ \t:=-]+(?:bn|hs)[-0-9]))(?![a-z])"
    r"(?:[ \t]+(?:gia lap|ghi tren phieu|ghi nhan|thanh|la)\b)?"
    + SEP
    + r"(?P<value>[a-z0-9]+(?:[-/][a-z0-9]+)*)(?!\w|[-/][a-z0-9])"
)
# Provincial codes used before the 2025 reorganization also appear on existing cards.
PROVINCE_CODES = frozenset(
    (
        "001 002 004 006 008 010 011 012 014 015 017 019 020 022 024 025 "
        "026 027 030 031 033 034 035 036 037 038 040 042 044 045 046 048 "
        "049 051 052 054 056 058 060 062 064 066 067 068 070 072 074 075 "
        "077 079 080 082 083 084 086 087 089 091 092 093 094 095 096"
    ).split()
)


def _birth_year(value: str, today: date) -> int | None:
    """Return the birth year for a calendar-valid candidate at or before today."""
    parts = re.findall(r"[0-9]+", value)
    if len(parts) == 1:
        year = int(parts[0])
        return year if 1900 <= year <= today.year else None
    if len(parts[0]) == 4:
        year, month, day = map(int, parts)
    else:
        day, month, year = map(int, parts)
        if len(parts[-1]) == 2:
            year += 2000 if year <= today.year % 100 else 1900
        elif len(parts[-1]) != 4:
            return None
    try:
        return year if 1900 <= year and date(year, month, day) <= today else None
    except ValueError:
        return None


def _date_match(text: str, offset: int, require_nearby: bool = True) -> re.Match[str] | None:
    """Find a date-shaped value after a bounded gap with no intervening clinical cue."""
    match = (
        DATE_VALUE.search(text, offset, min(len(text), offset + 103))
        if require_nearby
        else (DATE_VALUE.match(text, offset))
    )
    if match is None:
        return None
    start, end = match.span()
    gap = text[offset:start]
    if require_nearby and (
        len(gap) > 75 or not DATE_GAP.fullmatch(gap) or OTHER_DATE_FIELD.search(gap)
    ):
        return None
    separators = set(re.findall(r"[/.-]", match[0]))
    if len(separators) > 1 or (end < len(text) and text[end].isalnum()):
        return None
    return match


def _birth_dates(text: str) -> Iterator[re.Match[str]]:
    """Yield contextual birth dates or years, including both sides of a correction."""
    seen: set[tuple[int, int]] = set()
    for cue in DOB_CUE.finditer(text):
        if cue[0].startswith("sinh") and re.search(
            r"\b(?:hoc|thi)[ \t]+$", text[max(0, cue.start() - 16) : cue.start()]
        ):
            continue
        first = _date_match(text, cue.end())
        if first is None:
            continue
        if first.span() not in seen:
            seen.add(first.span())
            yield first
        gap = text[cue.end() : first.start()]
        if not re.search(r"\btu\b", gap):
            continue
        link = DATE_CORRECTION.match(text, first.end())
        if link is not None:
            offset = link.end()
            while offset < len(text) and text[offset] in " \t":
                offset += 1
            second = _date_match(text, offset, require_nearby=False)
            if second is not None and second.span() not in seen:
                seen.add(second.span())
                yield second


def _id_score(cue: str, value: str, years: set[int], today: date) -> float | None:
    """Score an explicitly labeled ID and use known structure only as positive evidence."""
    if not 3 <= len(value) <= 32 or not re.search(r"[0-9]", value):
        return None
    valid = True
    if cue in {"cccd", "can cuoc", "can cuoc cong dan"}:
        valid = bool(re.fullmatch(r"[0-9]{12}", value)) and value[:3] in PROVINCE_CODES
        if valid:
            year = 1900 + int(value[3]) // 2 * 100 + int(value[4:6])
            valid = year <= today.year and (len(years) != 1 or year in years)
    elif cue in {"cmnd", "chung minh nhan dan"}:
        valid = bool(re.fullmatch(r"[0-9]{9}", value))
    elif cue == "ho chieu":
        valid = bool(re.fullmatch(r"[a-z]{1,2}[0-9]{7,8}", value))
    elif cue.endswith("bhyt"):
        valid = bool(re.fullmatch(r"(?:[a-z]{2})?[0-9]{10,13}", value))
    return 0.97 if valid else 0.81


def _numeric_spans(text: str) -> Iterator[tuple[int, int]]:
    """Yield whole number runs, splitting only before a new full compact number."""
    for run in PHONE_RUN.finditer(text):
        start, end = run.span()
        if re.match(r"[ .\t-]+[0-9]", text[end : end + 16]):
            continue
        for split in PHONE_SEPARATOR.finditer(text, start, end):
            yield start, split.start()
            start = split.end()
        yield start, end


def _phone_context(text: str, start: int, end: int, previous: int | None) -> tuple[bool, bool]:
    """Return contact-context and competing-field flags from the surrounding clause."""
    left = text[max(0, start - 85) : start]
    field = CONTACT_FIELD_END.split(left)[-1]
    cues = [item for item in PHONE_LOCATOR.finditer(field) if PHONE_CUE.match(field, item.start())]
    cue_end = cues[-1].end() if cues else 0
    negative = bool(NON_PHONE.search(field, cue_end))
    right = text[end : end + 35]
    negative |= bool(re.match(r"[ \t]+(?:la[ \t]+)?(?:so[ \t]+)?(?:luu kho|ma lo|dong)\b", right))
    if negative:
        return False, True
    if cues:
        return True, False
    if PHONE_EXT.search(left):
        return True, False
    if previous is not None and PHONE_EXT_SHORT.search(field) and start - previous <= 28:
        return True, False
    block = CONTACT_BLOCK.search(left)
    if block and re.fullmatch(r"[ \t:]*\r?\n[ \t]*(?:[-*][ \t]*)?", left[block.end() :]):
        return True, False
    return False, False


def phone_structure(value: str) -> tuple[bool, bool]:
    """Return regional length and allocation signals; neither signal excludes a contact."""
    compact = re.sub(r"[^+0-9]", "", value)
    try:
        number = phonenumbers.parse(compact, "VN")
    except phonenumbers.NumberParseException:
        return False, False
    return (
        number.country_code == 84 and phonenumbers.is_possible_number(number),
        phonenumbers.is_valid_number_for_region(number, "VN"),
    )


def _phones(text: str) -> Iterator[Entity]:
    """Emit whole contextual numbers and rank standalone shapes using only additive signals."""
    previous: int | None = None
    for start, end in _numeric_spans(text):
        value = text[start:end]
        if end - start > 45 or len(re.findall(r"[0-9]", value)) < 3:
            continue
        context, negative = _phone_context(text, start, end, previous)
        if negative or (
            not context
            and DATE_VALUE.fullmatch(value)
            and re.search(r"[./-]", value)
            and not value.startswith("0")
        ):
            continue
        compact = re.sub(r"[^+0-9]", "", value)
        if not context and not STANDALONE_PHONE.fullmatch(compact):
            continue
        possible, valid = phone_structure(value)
        if context:
            previous = end
            score = 0.86 + 0.05 * possible + 0.06 * valid
            source = SOURCE
        else:
            score = round(0.4 + 0.2 * possible + 0.2 * valid, 2)
            source = STANDALONE_PHONE_SOURCE if score >= 0.5 else PHONE_REVIEW_SOURCE
        yield Entity(start=start, end=end, label="PHONE", source=source, score=score)


def structured_candidates(folded: str, today: date) -> Iterator[Entity]:
    """Yield contextual ID/DOB/PHONE spans in folded coordinates for original-offset mapping."""
    years: set[int] = set()
    for match in _birth_dates(folded):
        year = _birth_year(match[0], today)
        if year is not None:
            years.add(year)
        start, end = match.span()
        yield Entity(
            start=start, end=end, label="DOB", source=SOURCE, score=0.97 if year else 0.84
        )
    for match in ID.finditer(folded):
        score = _id_score(match["cue"], match["value"], years, today)
        if score is not None:
            start, end = match.span("value")
            yield Entity(start=start, end=end, label="ID", source=SOURCE, score=score)
    yield from _phones(folded)
