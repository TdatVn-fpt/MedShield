# apps/api/adapters/vi_names_places.py — Recognize contextual Vietnamese person and place spans.
import re
from collections.abc import Iterator
from unicodedata import category, normalize

from apps.api.schemas import Entity

SOURCE = "medshield-rules"
PROPAGATED = SOURCE + "+exact-name-repeat"
SURNAMES = frozenset(
    "nguyen tran le pham hoang huynh phan vu vo dang bui do ho ngo duong ly "
    "dinh truong luu cao mai to trinh dao phung lam chau thach ha".split()
)
PLACES = (
    "ha noi|ho chi minh|hai phong|da nang|can tho|hue|tuyen quang|lao cai|"
    "thai nguyen|lang son|cao bang|lai chau|dien bien|son la|phu tho|quang ninh|"
    "bac ninh|hung yen|ninh binh|thanh hoa|nghe an|ha tinh|quang tri|quang ngai|"
    "gia lai|khanh hoa|dak lak|lam dong|dong nai|tay ninh|dong thap|vinh long|"
    "an giang|ca mau|ha giang|yen bai|bac kan|hoa binh|vinh phuc|bac giang|"
    "hai duong|thai binh|ha nam|nam dinh|quang binh|quang nam|binh dinh|"
    "phu yen|kon tum|dak nong|ninh thuan|binh thuan|binh phuoc|binh duong|"
    "ba ria vung tau|long an|tien giang|ben tre|tra vinh|hau giang|"
    "soc trang|bac lieu|kien giang|thu duc|binh thanh|go vap|hoan kiem|"
    "ba dinh|cau giay|thanh xuan"
)
NAME_CUE = re.compile(
    r"\b(?:nguoi benh|benh nhan|ho(?: va)? ten(?: benh nhan)?|ten benh nhan|"
    r"nguoi (?:than|lien he)|bac si|bs\.|bn(?=[ \t]*[:=])|"
    r"ong|ba|anh|chi|(?:me|bo|vo|chong) cua benh nhan)(?!\w)"
    r"[ \t]*[:=–-]?[ \t]+|"
    r"\b(?:bn|ho(?: va)? ten|nguoi benh|benh nhan|bac si|bs\.)[ \t]*[:=][ \t]*"
)
WORD = re.compile(r"[^\W\d_]+(?:[-’'][^\W\d_]+)*")
NAME_STOP = re.compile(
    r"^(?:sinh|sn|tuoi|hien|da|den|nhap|xuat|kham|tai|bi|"
    r"co|khong|duoc|than phiet|trinh bay|cam thay|bao rang|noi rang|"
    r"dau|ho khan|ho nhieu|sot|can|dang (?:dieu tri|cho|duoc|nghi)|la|ma|cung|va|"
    r"theo (?:so|dia chi|yeu cau)|qua so|cho|goi|ghi|hoa don|xet nghiem|giuong|nam sinh)\b"
)
ADDR_CUE = re.compile(
    r"\b(?:dia chi(?: (?:cu tru|lien lac|nhan giay hen|thuong tru))?|"
    r"noi (?:o|cu tru)|cu tru|thuong tru|tam tru|que quan|hktt|d/c)"
    r"(?!\w)(?:[ \t]+(?:moi|cu)\b)?(?:[ \t]+la\b)?"
    r"[ \t]*[:=–-]?[ \t]*(?:\r?\n[ \t]*)?"
    r"(?:(?:ghi|in|luu) (?:tren|trong) (?:phieu|giay|ho so|so)[ \t]*[:=][ \t]*)?"
)
ADDR_END = re.compile(
    r"[;|!?]|(?<!\btp)(?<!\b[ptq])\.(?=\s|$)|"
    r"(?:,|\r?\n|[ \t]+)(?=[ \t]*(?:sdt|so dien thoai|dien thoai|"
    r"lien he|hen|tai kham|chan doan|ma|bac si|ngay sinh|sinh ngay|cccd|"
    r"xin cap nhat|cap nhat ho so|de nghi|bo dong cu|va so (?:di dong|dien thoai))\b)|"
    r"\r?\n(?![ \t]*(?:phuong|xa|quan|huyen|thanh pho|tinh|tp\.|p\.|q\.))|$"
)
ADDR_MARKER = re.compile(
    rf"\b(?:duong|ngo|hem|ngach|thon|ap|xom|to|khu pho|phuong|xa|"
    rf"quan|huyen|thi tran|thanh pho|tinh|tp\.|p\.|q\.|{PLACES})\b|^[0-9]+[ /-]"
)


def folded_text(text: str) -> tuple[str, list[int], list[int]]:
    """Fold case and accents while mapping each resulting character to original boundaries."""
    folded: list[str] = []
    starts: list[int] = []
    ends: list[int] = []
    for index, char in enumerate(text):
        value = normalize("NFD", char.casefold().replace("đ", "d"))
        symbols = [part for part in value if category(part) not in {"Mn", "Mc", "Me"}]
        if not symbols and ends:
            ends[-1] = index + 1
        for symbol in symbols:
            folded.append(symbol)
            starts.append(index)
            ends.append(index + 1)
    return "".join(folded), starts, ends


def _has_name_shape(words: list[str], folded_first: str) -> bool:
    """Use surname/initial capitalization as supporting evidence after a person cue."""
    return 2 <= len(words) <= 5 and (
        folded_first in SURNAMES or all(word[0].isupper() for word in words)
    )


def name_candidates(
    text: str, folded: str, starts: list[int], ends: list[int]
) -> Iterator[Entity]:
    """Propose names after explicit cues and return spans on the untouched original text."""
    for cue in NAME_CUE.finditer(folded):
        start = end = cue.end()
        words: list[str] = []
        first = ""
        while end < len(folded) and len(words) < 5:
            if NAME_STOP.match(folded[end : end + 24]):
                break
            word = WORD.match(folded, end)
            if word is None:
                break
            original = text[starts[word.start()] : ends[word.end() - 1]]
            if words and words[-1][0].isupper() and not original[0].isupper():
                break
            if not words:
                first = word[0]
            words.append(original)
            end = word.end()
            if end >= len(folded) or folded[end] not in " \t":
                break
            while end < len(folded) and folded[end] in " \t":
                end += 1
        while end > start and folded[end - 1] in " \t":
            end -= 1
        if _has_name_shape(words, first):
            yield Entity(
                start=starts[start], end=ends[end - 1], label="NAME", source=SOURCE, score=0.92
            )


def address_candidates(folded: str, starts: list[int], ends: list[int]) -> Iterator[Entity]:
    """Keep a street or named place after a residence cue and preserve original punctuation."""
    for cue in ADDR_CUE.finditer(folded):
        start = cue.end()
        stop = ADDR_END.search(folded, start, min(len(folded), start + 251))
        if stop is None:
            continue
        value = folded[start : stop.start()].rstrip(" \t\r\n,")
        if 3 <= len(value) <= 250 and ADDR_MARKER.search(value):
            end = ends[start + len(value) - 1]
            yield Entity(start=starts[start], end=end, label="ADDR", source=SOURCE, score=0.89)


def repeat_names(text: str, entities: list[Entity]) -> Iterator[Entity]:
    """Propose later exact, whole-name repetitions from confident seeds in the same note."""
    seeds: dict[str, Entity] = {}
    for entity in entities:
        if entity.label == "NAME" and entity.score >= 0.9:
            seeds.setdefault(text[entity.start : entity.end], entity)
    if not seeds:
        return
    alternatives = "|".join(re.escape(name) for name in sorted(seeds, key=len, reverse=True))
    for match in re.finditer(r"(?<!\w)(?:" + alternatives + r")(?!\w)", text):
        seed = seeds[match[0]]
        if match.start() >= seed.end and (
            match.end() == len(text) or not category(text[match.end()]).startswith("M")
        ):
            yield Entity(
                start=match.start(), end=match.end(), label="NAME", source=PROPAGATED, score=0.88
            )
