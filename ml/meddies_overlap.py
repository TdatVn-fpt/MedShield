# ml/meddies_overlap.py — Measure whole-corpus text and surface overlap without evaluation labels.
import re
from collections import Counter, defaultdict
from collections.abc import Iterable
from fractions import Fraction
from unicodedata import normalize

WORD = re.compile(r"[^\W_]+")
PHONE = re.compile(r"(?<!\w)\+?\d(?:[ .()\-]*\d){7,14}(?!\w)")
DATE = re.compile(
    r"(?<!\w)(?:ngày\s*)?(\d{1,4})(?:\s*[/.-]\s*|\s+tháng\s+)"
    r"(\d{1,2})(?:\s*[/.-]\s*|\s+năm\s+)(\d{1,4})(?!\w)"
)
Shingle = tuple[str, ...]
Pair = tuple[str, Shingle, Shingle]


def words(text: str) -> list[str]:
    """Tokenize NFC casefolded Unicode words, keeping accents and digit runs."""
    return WORD.findall(normalize("NFC", text).casefold())


def shingles(tokens: list[str], width: int) -> set[Shingle]:
    """Return contiguous fixed-width token shingles with set semantics."""
    return set(zip(*(tokens[offset:] for offset in range(width)), strict=False))


def max_similarity(evaluation: list[set[Shingle]], train: Iterable[str]) -> list[Fraction]:
    """Find exact maximum word 5-gram Jaccard against all train notes for each candidate."""
    index: defaultdict[Shingle, list[int]] = defaultdict(list)
    for pos, grams in enumerate(evaluation):
        for gram in grams:
            index[gram].append(pos)
    result = [Fraction(0) for _ in evaluation]
    for text in train:
        grams = shingles(words(text), 5)
        hits = Counter(pos for gram in grams for pos in index.get(gram, ()))
        for pos, count in hits.items():
            union = len(grams) + len(evaluation[pos]) - count
            current = result[pos]
            if count * current.denominator > current.numerator * union:
                result[pos] = Fraction(count, union)
    return result


def _phone(value: str) -> Shingle:
    """Normalize common Vietnam phone formatting and the +84/0 prefix."""
    digits = "".join(char for char in value if char.isdecimal())
    if digits.startswith("84") and len(digits) in {10, 11, 12}:
        digits = "0" + digits[2:]
    return (digits,)


def _date(match: tuple[str, str, str]) -> Shingle:
    """Normalize zero padding plus year-first date formats without guessing centuries."""
    left, month, right = match
    day, year = (right, left) if len(left) == 4 else (left, right)
    return tuple(str(int(part)) for part in (day, month, year))


def surface_keys(text: str, label: str) -> set[Shingle]:
    """Extract exact token surfaces and comparable phone or date formats from one string."""
    normalized = normalize("NFC", text).casefold()
    if label == "PHONE":
        return {_phone(match.group()) for match in PHONE.finditer(normalized)}
    return {_date(match) for match in DATE.findall(normalized)}


class SurfaceIndex:
    """Index co-occurring train NAME + PHONE/DOB while keeping candidate text label-blind."""

    def __init__(self) -> None:
        self._names_by_value: defaultdict[tuple[str, Shingle], set[Shingle]] = defaultdict(set)

    def add(self, names: set[Shingle], values: set[tuple[str, Shingle]]) -> None:
        """Add combinations within the same train document only."""
        for value in values:
            self._names_by_value[value].update(names)

    def matches(self, text: str) -> set[Pair]:
        """Return observed train combinations found in contiguous evaluation text tokens."""
        tokens = words(text)
        result = set()
        windows: dict[int, set[Shingle]] = {}
        for label in ("PHONE", "DOB"):
            for value in surface_keys(text, label):
                for name in self._names_by_value.get((label, value), ()):
                    if len(name) not in windows:
                        windows[len(name)] = shingles(tokens, len(name))
                    if name in windows[len(name)]:
                        result.add((label, name, value))
        return result
