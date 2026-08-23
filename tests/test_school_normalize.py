from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from school_normalize import CanonicalSchool, normalize_school  # noqa: E402

HKUST = CanonicalSchool(
    id="hkust",
    name_zh="香港科技大学",
    name_en="The Hong Kong University of Science and Technology",
    country="中国香港",
)


@pytest.mark.parametrize(
    "claimed",
    ["HKUST", "hkust", "港科大", "香港科技大学", "  HKUST  "],
)
def test_hkust_aliases_unify(claimed: str) -> None:
    got = normalize_school(claimed)
    assert got == HKUST


def test_hkust_full_english_matches_abbreviation() -> None:
    assert normalize_school("The Hong Kong University of Science and Technology") == normalize_school(
        "HKUST"
    )


def test_hkust_gz_is_not_hkust() -> None:
    got = normalize_school("港科广")
    assert got is not None
    assert got.id == "hkust-gz"
    assert got != HKUST


@pytest.mark.parametrize(
    ("claimed", "school_id", "country"),
    [
        ("MIT", "mit", "美国"),
        ("Massachusetts Institute of Technology", "mit", "美国"),
        ("清华", "tsinghua", "中国"),
        ("清华大学", "tsinghua", "中国"),
        ("NUS", "nus", "新加坡"),
        ("National University of Singapore", "nus", "新加坡"),
    ],
)
def test_common_aliases(claimed: str, school_id: str, country: str) -> None:
    got = normalize_school(claimed)
    assert got is not None
    assert got.id == school_id
    assert got.country == country


def test_abbreviation_equals_full_name() -> None:
    assert normalize_school("MIT") == normalize_school("Massachusetts Institute of Technology")
    assert normalize_school("清华") == normalize_school("清华大学")
    assert normalize_school("NUS") == normalize_school("National University of Singapore")


@pytest.mark.parametrize(
    "claimed",
    [
        "",
        "   ",
        "asdfghjkl-not-a-university-zzz",
        "qwertyuiop学校12345",
        "COMMITTEE",
        "randomlab",
    ],
)
def test_garbage_is_unrecognized(claimed: str) -> None:
    assert normalize_school(claimed) is None


def test_alias_check_fixture() -> None:
    check = json.loads((ROOT / "tests/fixtures/school_alias_check.json").read_text(encoding="utf-8"))
    want = check["must_unify"]
    results = [normalize_school(alias) for alias in want["aliases"]]
    assert all(row is not None for row in results)
    assert {row.id for row in results} == {want["school_id"]}
    assert {row.name_zh for row in results} == {want["name_zh"]}
    assert {row.country for row in results} == {want["country"]}
    for alias in check["must_not_unify_with"]["aliases"]:
        got = normalize_school(alias)
        assert got is not None
        assert got.id == check["must_not_unify_with"]["school_id"]
