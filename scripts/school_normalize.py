"""Map a claimed school string to a canonical school, or unrecognized."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from _paths import SCHOOLS_PATH


@dataclass(frozen=True)
class CanonicalSchool:
    id: str
    name_zh: str
    name_en: str
    country: str


def fold_school_text(value: str) -> str:
    """Case-fold, NFKC, and collapse punctuation/whitespace for alias lookup."""
    text = unicodedata.normalize("NFKC", value or "").strip().lower()
    text = re.sub(r"[\s\-_]+", " ", text)
    text = re.sub(r"[.,，。;；:：()（）\[\]【】]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


@lru_cache(maxsize=1)
def _alias_index(path: str) -> dict[str, CanonicalSchool]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    index: dict[str, CanonicalSchool] = {}
    for row in payload["schools"]:
        school = CanonicalSchool(
            id=row["id"],
            name_zh=row["name_zh"],
            name_en=row["name_en"],
            country=row["country"],
        )
        for alias in row["aliases"]:
            key = fold_school_text(alias)
            if not key:
                continue
            existing = index.get(key)
            if existing and existing.id != school.id:
                raise ValueError(f"alias {alias!r} maps to both {existing.id} and {school.id}")
            index[key] = school
    return index


def normalize_school(
    claimed: str,
    *,
    schools_path: Path | None = None,
) -> CanonicalSchool | None:
    """Return canonical school for an exact alias match after folding, else None."""
    key = fold_school_text(claimed)
    if not key:
        return None
    path = str(schools_path or SCHOOLS_PATH)
    return _alias_index(path).get(key)
