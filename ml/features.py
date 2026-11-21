# ml/features.py — Extract shared CRF features without changing source offsets.
from collections.abc import Sequence
from unicodedata import normalize

from ml.tokenization import Token

FEATURES_VERSION = 1
Feature = str | bool | int


def extract_features(text: str, tokens: Sequence[Token]) -> list[dict[str, Feature]]:
    """Extract word shapes and local context from original token slices for train and infer."""
    words = [normalize("NFC", text[token.start : token.end]) for token in tokens]
    folded = [word.casefold() for word in words]
    features: list[dict[str, Feature]] = []
    for index, word in enumerate(words):
        lower = folded[index]
        current: dict[str, Feature] = {
            "bias": 1,
            "word": lower,
            "prefix": lower[:2],
            "suffix": lower[-3:],
            "title": word.istitle(),
            "upper": word.isupper(),
            "alpha": word.isalpha(),
            "digits": word.isdecimal(),
        }
        for offset in (-3, -2, -1, 1, 2, 3):
            neighbor = index + offset
            if 0 <= neighbor < len(words):
                current[f"{offset}:word"] = folded[neighbor]
                current[f"{offset}:title"] = words[neighbor].istitle()
                current[f"{offset}:digits"] = words[neighbor].isdecimal()
            else:
                current[f"{offset}:boundary"] = True
        if index:
            gap = text[tokens[index - 1].end : tokens[index].start]
            current["adjacent"] = not gap
            current["after_newline"] = "\n" in gap or "\r" in gap
        features.append(current)
    return features
