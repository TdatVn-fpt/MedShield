# ml/meddies_mapping_rules.py — Apply owner-reviewed boundaries to Meddies train spans.
import re
from collections import Counter
from ipaddress import ip_address
from typing import Any
from unicodedata import normalize

from apps.api.adapters.vi_names_places import SURNAMES, folded_text

TITLE = re.compile(
    r"^\s*(?:bac si(?:\s+(?:chuyen khoa|ck)\s*(?:ii|i))?|"
    r"duoc si|dieu duong(?: vien)?|y si|ho sinh|"
    r"bs(?:ck\s*(?:ii|i))?|dr|pgs|gs|ths|ts|mr|mrs|ms)"
    r"(?:\.\s*|\s*[:：]\s*|\s+|$)"
)
HONORIFIC = re.compile(r"^\s*(ong|ba|anh|chi)\s+")
FACILITY = (
    r"(?:benh[ _-]?vien|phong[ _-]?kham|co[ _-]?so[ _-]?y[ _-]?te|"
    r"trung[ _-]?tam[ _-]?(?:y[ _-]?te|kham[ _-]?benh)|nha[ _-]?thuoc|"
    r"hospital|clinic|health[ _-]?(?:care[ _-]?)?(?:center|centre|facility)|pharmacy)"
)
ADDRESS = r"(?:dia[ _-]?chi|address|location)"
FACILITY_ADDRESS = re.compile(
    rf"\b(?:{ADDRESS}(?:[ _-]+(?:cua[ _-]+|of[ _-]+|lien[ _-]+he[ _-]+))?[ _-]*{FACILITY}"
    rf"|{FACILITY}[ _-]*{ADDRESS})(?:[ _-]*(?:lien[ _-]*he|line[12]?|city|district))?\b"
)
PERSON_ADDRESS = re.compile(
    r"\b(?:dia chi (?:nha|cu tru|thuong tru|tam tru|nguoi than|benh nhan|cua benh nhan|nhan thu)"
    r"|(?:patient|home|residential|registered)[ _-]+address|noi o|que quan|ho khau)\b"
)
FACILITY_HEADING = re.compile(
    rf"^(?:(?:ten|nguon|name)[ _-]+)?{FACILITY}\b|"
    rf"^(?:don vi|unit|department)[ \t]*[:：|｜][ \t]*{FACILITY}\b"
)
FACILITY_INLINE = re.compile(rf"\b{FACILITY}[^;|.!?\r\n]*,\s*(?:dia chi|address)[\s*\"'`:=：]*$")
ADDRESS_FIELD = re.compile(rf"^(?:{ADDRESS})(?:[ _-]+lien[ _-]+he)?$")
FACILITY_DEPARTMENT = re.compile(r"^(?:khoa|department|don vi)\b")
IP_FIELD = re.compile(r"\b(?:dia[ _-]?chi[ _-]+ip|ip[ _-]?address|ipv[46])\b")
IP_WITH_PORT = re.compile(r"^(?:\[([^\]]+)\]|(\d+(?:\.\d+){3}))(?::\d+)?$")

DOCUMENT_KIND = (
    r"(?:don(?:[ _-]+thuoc)?|phieu(?:[ _-]+[^:：|;,\r\n]{1,45})?|toa[ _-]+thuoc|"
    r"hoa[ _-]+don|bien[ _-]+lai|(?:(?:ket[ _-]+qua|mau)[ _-]+)?xet[ _-]+nghiem|"
    r"don[ _-]+yeu[ _-]+cau|giao[ _-]+dich|yeu[ _-]+cau(?:[ _-]+boi[ _-]+thuong)?|"
    r"lan[ _-]+kham|luot[ _-]+kham|"
    r"prescription|order|invoice|receipt|claim|result|test|specimen|request|encounter|"
    r"document|form|referral)"
)
ID_KIND = (
    r"(?:cccd(?:/cmnd)?|cmnd(?:/cccd)?|can[ _-]+cuoc(?:[ _-]+cong[ _-]+dan)?|"
    r"ho[ _-]+chieu|bhyt|bhxh|(?:the[ _-]+)?bao[ _-]+hiem(?:[ _-]+y[ _-]+te)?|"
    r"benh[ _-]+nhan|nguoi[ _-]+benh|benh[ _-]+an|ho[ _-]+so(?:[ _-]+benh[ _-]+an)?|"
    r"bac[ _-]+si|nhan[ _-]+vien(?:[ _-]+y[ _-]+te)?|hop[ _-]+dong|tai[ _-]+khoan|"
    r"patient|medical[ _-]+record|insurance|policy|practitioner|staff)"
)
LABEL_PREFIX = r"(?:ma(?:[ _-]+so)?|so|id|code|number)"
DOCUMENT_FIELD = re.compile(
    rf"(?:\b{LABEL_PREFIX}[ _-]+{DOCUMENT_KIND}|"
    rf"\b{DOCUMENT_KIND}[ _-]*{LABEL_PREFIX})"
    r"(?:[ \t]+(?:la|so|is|no\.?))?$"
)
PERSON_ID_FIELD = re.compile(
    rf"^\s*(?:(?:{LABEL_PREFIX})(?:[ _-]+{ID_KIND})?|{ID_KIND}"
    rf"(?:[ _-]+{LABEL_PREFIX})?)[*\"'` _-]*[:：=|｜][*\"'`\s]*"
)
INSURANCE_ANCHOR = re.compile(r"^\s*bhyt\s*[-–—−]\s*(?=\w)")
NON_PERSON_FIELD = re.compile(
    rf"\b(?:{LABEL_PREFIX}[ _-]+(?:phong(?:[ _-]+benh)?|giuong|thiet[ _-]+bi|"
    r"icd(?:-?10)?|chan[ _-]+doan|phien(?:[ _-]+dang[ _-]+nhap)?|thong[ _-]+diep|"
    r"thuoc|benh[ _-]+vien|phong[ _-]+kham|co[ _-]+so[ _-]+y[ _-]+te)|"
    r"(?:device|room|bed|diagnosis|session|message|hospital|clinic|facility)"
    rf"[ _-]*{LABEL_PREFIX})$"
)
REFERENCE_RANGE = re.compile(r"^\s*\d+(?:[.,]\d+)?\s*(?:[-–—−]|den|to)\s*\d+(?:[.,]\d+)?\s*$")
REFERENCE_FIELD = re.compile(
    r"\b(?:(?:khoang|gia tri|muc|nguong) tham chieu|khoang binh thuong|reference range)\b"
)
LAB_UNITS = re.compile(r"^\s*(?:mg/dl|mmol/l|g/dl|ng/ml|iu/l|u/l|umol/l)(?=\W|$)")
BEFORE_VALUE = re.compile(r"[\s*\"'`|｜:=：]+$")
FIELD_BREAK = re.compile(r"[;|｜]|(?<!\d)\.(?=\s|$)")

CORRECTION_LABELS = {
    "name_title_trimmed": ("NAME", "trimmed"),
    "name_title_only_removed": ("NAME", "removed"),
    "addr_facility_removed": ("ADDR", "removed"),
    "addr_ip_removed": ("ADDR", "removed"),
    "id_document_code_removed": ("ID", "removed"),
    "id_lab_reference_removed": ("ID", "removed"),
    "id_non_person_code_removed": ("ID", "removed"),
    "id_field_trimmed": ("ID", "trimmed"),
    "id_bhyt_anchor_trimmed": ("ID", "trimmed"),
    "id_field_only_removed": ("ID", "removed"),
}


def _fold(text: str) -> str:
    """Fold a lookup copy for Vietnamese cues without using it as source text."""
    return folded_text(text)[0]


def _field(prefix: str) -> str:
    """Return the last field before a value, unwrapping table and Markdown separators."""
    prefix = BEFORE_VALUE.sub("", prefix)
    return FIELD_BREAK.split(prefix)[-1].strip(" \t#-*\"'`•")


def _included_field(value: str) -> str:
    """Extract a field written inside a publisher span when it has an explicit delimiter."""
    prefix = re.split(r"[:：=|｜]", value, maxsplit=1)
    return _field(prefix[0]) if len(prefix) > 1 else ""


def _honorific_length(value: str, remainder: str, position: int, ends: list[int]) -> int:
    """Recognize courteous prefixes when diacritics or a following full name identify them."""
    match = HONORIFIC.match(remainder)
    if not match:
        return 0
    words = remainder[match.end() :].split()
    if len(words) >= 2 and words[0] in SURNAMES:
        return match.end()
    original_start = ends[position + match.start(1) - 1] if position + match.start(1) else 0
    original_end = ends[position + match.end(1) - 1]
    title = normalize("NFC", value[original_start:original_end]).casefold()
    if title in {"ông", "bà", "chị"} and words and words[0] not in {"gai", "trai"}:
        return match.end()
    return 0


def _name_start(value: str) -> int:
    """Return a code-point start after stacked professional titles and clear honorifics."""
    folded, _, ends = folded_text(value)
    boundary = 0
    while boundary < len(folded):
        remainder = folded[boundary:]
        match = TITLE.match(remainder)
        length = match.end() if match else _honorific_length(value, remainder, boundary, ends)
        if not length:
            break
        boundary += length
    return _skip_space(value, ends[boundary - 1]) if boundary else 0


def _skip_space(value: str, start: int) -> int:
    """Advance an edited start past original Unicode whitespace without re-encoding text."""
    while start < len(value) and value[start].isspace():
        start += 1
    return start


def _is_ip(value: str, left: str) -> bool:
    """Recognize IP values, including ports and invalid values explicitly labeled as IP."""
    candidate = value.strip()
    if IP_FIELD.search(_field(left)) or IP_FIELD.search(_included_field(candidate)):
        return True
    if match := IP_WITH_PORT.fullmatch(candidate):
        candidate = match[1] or match[2]
    try:
        ip_address(candidate)
    except ValueError:
        return False
    return True


def _facility_address(value: str, left: str, previous: list[str]) -> bool:
    """Use facility-specific fields or an immediately associated facility header for ADDR."""
    field = _field(left)
    included = _included_field(value)
    if PERSON_ADDRESS.search(field) or PERSON_ADDRESS.search(included):
        return False
    if FACILITY_ADDRESS.search(field) or FACILITY_ADDRESS.search(included):
        return True
    if FACILITY_INLINE.search(left):
        return True
    if FACILITY_HEADING.match(value.strip()) or (
        left.lstrip().startswith("msh|")
        and left.count("|") in {3, 5}
        and re.search(FACILITY, left)
    ):
        return True
    address_field = next(iter(filter(None, (included, field))), "")
    if address_field and not ADDRESS_FIELD.fullmatch(address_field):
        return False
    for line in reversed(previous[-2:]):
        heading = line.strip(" \t#-*\"'`🏥")
        if FACILITY_HEADING.match(heading):
            return True
        if not heading or FACILITY_DEPARTMENT.match(heading):
            continue
        return False
    return False


def _is_reference_range(value: str, left: str, right: str) -> bool:
    """Identify a numeric laboratory range from its field, unit, or HL7 OBX-7 column."""
    if left.lstrip().startswith("obx|") and left.count("|") == 7:
        return True
    if not REFERENCE_RANGE.fullmatch(value):
        return False
    return bool(REFERENCE_FIELD.search(_field(left)) or LAB_UNITS.match(right))


def _id_entity(
    text: str, start: int, end: int, left: str, corrections: Counter[str]
) -> int | None:
    """Drop ruled-out ID values and return the original start after field and BHYT cues."""
    value = text[start:end]
    folded, _, ends = folded_text(value)
    fields = (_field(left), _included_field(folded))
    segment, _, _ = left.lstrip().partition("|")
    pipe_count = left.count("|")
    if (segment in {"obr", "orc"} and pipe_count in {2, 3}) or any(
        DOCUMENT_FIELD.search(field) for field in fields
    ):
        corrections["id_document_code_removed"] += 1
        return None
    if (segment, pipe_count) in {("msh", 9), ("msa", 2)} or any(
        NON_PERSON_FIELD.search(field) for field in fields
    ):
        corrections["id_non_person_code_removed"] += 1
        return None
    boundary = 0
    if match := PERSON_ID_FIELD.match(folded):
        boundary = match.end()
    if _is_reference_range(folded[boundary:], left, _fold(text[end : end + 18])):
        corrections["id_lab_reference_removed"] += 1
        return None
    if match := INSURANCE_ANCHOR.match(folded[boundary:]):
        if boundary:
            corrections["id_field_trimmed"] += 1
        corrections["id_bhyt_anchor_trimmed"] += 1
        return start + _skip_space(value, ends[boundary + match.end() - 1])
    if boundary:
        if not folded[boundary:].strip():
            corrections["id_field_only_removed"] += 1
            return None
        corrections["id_field_trimmed"] += 1
        return start + _skip_space(value, ends[boundary - 1])
    return start


def remap_entities(
    text: str, entities: list[dict[str, Any]], corrections: Counter[str]
) -> list[dict[str, Any]]:
    """Trim or drop validated train spans while preserving original text and DOB/PHONE."""
    revised = []
    for entity in entities:
        start, end, label = entity["start"], entity["end"], entity["label"]
        if label == "NAME":
            offset = _name_start(text[start:end])
            if offset >= end - start:
                corrections["name_title_only_removed"] += 1
                continue
            if offset:
                corrections["name_title_trimmed"] += 1
                start += offset
        if label in {"ADDR", "ID"}:
            *previous, left = _fold(text[max(0, start - 420) : start]).split("\n")
            if label == "ID":
                revised_start = _id_entity(text, start, end, left, corrections)
                if revised_start is None:
                    continue
                start = revised_start
            else:
                value = _fold(text[start:end])
                if _is_ip(value, left):
                    corrections["addr_ip_removed"] += 1
                    continue
                if _facility_address(value, left, previous):
                    corrections["addr_facility_removed"] += 1
                    continue
        revised.append({**entity, "start": start})
    return revised
