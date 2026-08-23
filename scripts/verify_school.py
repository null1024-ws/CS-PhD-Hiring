"""Offline school verification from claimed text + optional homepage / OpenAlex strings."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from _paths import SCHOOLS_PATH
from school_normalize import CanonicalSchool, fold_school_text, normalize_school


@dataclass
class SchoolEvidence:
    source: str
    url: str
    snippet: str
    fetched_at: str = "fixture"


@dataclass
class SchoolVerification:
    school_claimed: str
    school_canonical: str
    school_country: str
    school_status: str
    evidence: list[SchoolEvidence] = field(default_factory=list)
    suggested_school: str | None = None


@lru_cache(maxsize=1)
def _schools(path: str) -> list[tuple[CanonicalSchool, list[str]]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    rows: list[tuple[CanonicalSchool, list[str]]] = []
    for item in payload["schools"]:
        school = CanonicalSchool(
            id=item["id"],
            name_zh=item["name_zh"],
            name_en=item["name_en"],
            country=item["country"],
        )
        aliases = sorted(item["aliases"], key=len, reverse=True)
        rows.append((school, aliases))
    return rows


def schools_mentioned(text: str, *, schools_path: Path | None = None) -> list[CanonicalSchool]:
    if not text:
        return []
    found: list[CanonicalSchool] = []
    seen: set[str] = set()
    for school, aliases in _schools(str(schools_path or SCHOOLS_PATH)):
        for alias in aliases:
            if re.search(r"[A-Za-z]", alias) and len(alias) <= 5:
                hit = re.search(rf"(?<![\w.]){re.escape(alias)}(?![\w.])", text, re.I)
            else:
                hit = fold_school_text(alias) in fold_school_text(text) or alias in text
            if hit and school.id not in seen:
                seen.add(school.id)
                found.append(school)
                break
    return found


def verify_school(
    claimed: str | None,
    *,
    homepage_text: str | None = None,
    homepage_url: str | None = None,
    openalex_affiliations: list[str] | None = None,
    schools_path: Path | None = None,
) -> SchoolVerification:
    claimed = (claimed or "").strip()
    canonical = normalize_school(claimed, schools_path=schools_path) if claimed else None
    external_texts = [homepage_text or ""]
    external_texts.extend(openalex_affiliations or [])
    mentioned: list[CanonicalSchool] = []
    for blob in external_texts:
        mentioned.extend(schools_mentioned(blob, schools_path=schools_path))

    unique: dict[str, CanonicalSchool] = {s.id: s for s in mentioned}
    evidence: list[SchoolEvidence] = []
    if homepage_text and homepage_url:
        evidence.append(
            SchoolEvidence(
                source="homepage",
                url=homepage_url,
                snippet=homepage_text[:180],
            )
        )
    if openalex_affiliations:
        evidence.append(
            SchoolEvidence(
                source="openalex",
                url="https://api.openalex.org",
                snippet="; ".join(openalex_affiliations)[:180],
            )
        )

    if not canonical:
        return SchoolVerification(
            school_claimed=claimed or "未知",
            school_canonical=claimed or "未知",
            school_country="",
            school_status="unverified",
            evidence=evidence,
        )

    if not unique:
        return SchoolVerification(
            school_claimed=claimed,
            school_canonical=canonical.name_zh,
            school_country=canonical.country,
            school_status="unverified",
            evidence=evidence,
        )

    if canonical.id in unique:
        return SchoolVerification(
            school_claimed=claimed,
            school_canonical=canonical.name_zh,
            school_country=canonical.country,
            school_status="verified",
            evidence=evidence,
        )

    other = next(iter(unique.values()))
    return SchoolVerification(
        school_claimed=claimed,
        school_canonical=canonical.name_zh,
        school_country=canonical.country,
        school_status="conflict",
        evidence=evidence,
        suggested_school=other.name_zh,
    )
