"""Merge opportunities that refer to the same PI + school (or homepage)."""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlparse

from school_normalize import fold_school_text


def normalize_pi_name(name: str) -> str:
    return fold_school_text(name or "")


def homepage_host(url: str | None) -> str | None:
    if not url:
        return None
    host = urlparse(url).netloc.lower()
    return host or None


def identity_key(
    name: str,
    school_canonical: str | None,
    homepage_url: str | None = None,
) -> str | None:
    """None means do not merge with anyone else."""
    person = normalize_pi_name(name)
    if not person:
        return None
    school = fold_school_text(school_canonical or "")
    if school and school != fold_school_text("未知"):
        return f"{person}|{school}"
    host = homepage_host(homepage_url)
    if host:
        return f"{person}|host:{host}"
    return None


@dataclass
class MergedPI:
    key: str
    name: str
    school_canonical: str
    school_country: str
    school_status: str
    homepage_url: str | None
    research_areas: list[str] = field(default_factory=list)
    opportunity_types: list[str] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)
    records: list[dict] = field(default_factory=list)


def _uniq(items: list[str]) -> list[str]:
    out: list[str] = []
    for item in items:
        if item and item not in out:
            out.append(item)
    return out


def merge_records(records: list[dict]) -> list[MergedPI]:
    groups: dict[str, MergedPI] = {}
    singles: list[MergedPI] = []
    for i, rec in enumerate(records):
        key = identity_key(
            rec.get("name") or rec.get("pi_name") or "",
            rec.get("school_canonical"),
            rec.get("homepage_url"),
        )
        if key is None:
            singles.append(
                MergedPI(
                    key=f"single:{i}",
                    name=rec.get("name") or rec.get("pi_name") or "未知",
                    school_canonical=rec.get("school_canonical") or "未知",
                    school_country=rec.get("school_country") or "",
                    school_status=rec.get("school_status") or "unverified",
                    homepage_url=rec.get("homepage_url"),
                    research_areas=list(rec.get("research_areas") or []),
                    opportunity_types=list(rec.get("opportunity_types") or rec.get("types") or []),
                    sources=[rec.get("source") or {}],
                    records=[rec],
                )
            )
            continue
        if key not in groups:
            groups[key] = MergedPI(
                key=key,
                name=rec.get("name") or rec.get("pi_name") or "",
                school_canonical=rec.get("school_canonical") or "",
                school_country=rec.get("school_country") or "",
                school_status=rec.get("school_status") or "unverified",
                homepage_url=rec.get("homepage_url"),
            )
        group = groups[key]
        group.research_areas = _uniq(group.research_areas + list(rec.get("research_areas") or []))
        group.opportunity_types = _uniq(
            group.opportunity_types + list(rec.get("opportunity_types") or rec.get("types") or [])
        )
        src = rec.get("source") or {}
        if src:
            group.sources.append(src)
        group.records.append(rec)
        if rec.get("school_status") == "conflict":
            group.school_status = "conflict"
        elif group.school_status != "conflict" and rec.get("school_status") == "verified":
            group.school_status = "verified"
        if rec.get("homepage_url") and not group.homepage_url:
            group.homepage_url = rec.get("homepage_url")
    return list(groups.values()) + singles
