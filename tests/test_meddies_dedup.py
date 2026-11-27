# tests/test_meddies_dedup.py — Check exact overlap, source-blind packets and surface pairs.
import json
from fractions import Fraction

import pytest

from ml.meddies_dedup import blind_split
from ml.meddies_overlap import SurfaceIndex, max_similarity, shingles, surface_keys, words
from ml.phase_e_types import IntakeError


def test_whole_corpus_jaccard_matches_brute_force() -> None:
    """Check exact maxima, including disjoint documents and Jaccard exactly one half."""
    train = ["a b c d e f g", "HỒ sơ khoa mắt", "ngày khám mới số năm"]
    evaluation = ["a b c d e f", "a b c d e f x", "không gặp bất kỳ cụm nào"]
    grams = [shingles(words(text), 5) for text in evaluation]
    train_grams = [shingles(words(text), 5) for text in train]
    expected = [max(Fraction(len(a & b), len(a | b)) for b in train_grams) for a in grams]
    assert max_similarity(grams, train) == expected == [Fraction(2, 3), Fraction(1, 2), 0]


def test_surface_pair_requires_both_values_in_same_train_and_candidate() -> None:
    """Catch equivalent phone/date formats while ignoring unrelated names or cross-note pairs."""
    index = SurfaceIndex()
    name = tuple(words("Trần Minh An"))
    other = tuple(words("Trần Minh Anh"))
    index.add({name}, {("DOB", key) for key in surface_keys("04/02/1990", "DOB")})
    index.add({other}, {("PHONE", key) for key in surface_keys("090.123.4567", "PHONE")})
    assert {m[0] for m in index.matches("Trần Minh An, sinh ngày 4 tháng 2 năm 1990")} == {"DOB"}
    assert {m[0] for m in index.matches("TRẦN MINH ANH: +84 90 123 4567")} == {"PHONE"}
    assert not index.matches("Trần Minh An: +84 90 123 4567")
    assert not index.matches("Trần Minh Anh, sinh 1990-02-04")


def test_blind_split_deterministic_and_stratified() -> None:
    """Keep both packets label-free, disjoint, and large enough for the intended workflow."""
    rows = [
        {"text": f"a{i} b{i} c{i} d{i} e{i}", "info": {"document_type": "A" if i < 100 else "B"}}
        for i in range(200)
    ]
    with pytest.raises(IntakeError):
        blind_split(rows[:-1])
    files, report = blind_split(rows)
    assert blind_split(list(reversed(rows))) == (files, report)
    validation = [json.loads(line) for line in files["validation-blind.jsonl"].splitlines()]
    test = [json.loads(line) for line in files["test-blind.jsonl"].splitlines()]
    assert len(test) == 150 and len(validation) == 50
    assert all(set(row) == {"note_id", "text"} for row in validation + test)
    assert {row["note_id"] for row in validation}.isdisjoint(row["note_id"] for row in test)
    assert report["test"]["document_types"] == {"A": 75, "B": 75}
    assert report["test_max_jaccard_against_validation"] == 0
