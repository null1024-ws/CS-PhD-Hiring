#!/usr/bin/env python3
"""bundle → extract → relevance → agency → verify → dedup → listings.json"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from _paths import AUDIT_PATH, BUNDLES_DIR, LISTINGS_PATH, PIS_DIR, ensure_dirs
from agency import classify_contact, classify_source_kind, should_list_source
from audit_pipeline import write_audit
from content_bundle import bundle_extract_text, bundle_visible_text, flatten_collected_note
from dedup import merge_records
from extract import extract_opportunities, is_main_table_name
from relevance import classify_relevance
from school_normalize import normalize_school
from verify_school import verify_school

CUTOFF_DAYS = 18 * 30


def load_notes(input_dir: Path) -> list[dict]:
    notes = []
    for path in sorted(input_dir.glob("*.json")):
        notes.append(flatten_collected_note(json.loads(path.read_text(encoding="utf-8"))))
    return notes


def _slug(name: str, school: str) -> str:
    raw = f"{name}-{school}".lower()
    slug = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", raw).strip("-")
    return slug or "unknown"


def process_note(note: dict) -> list[dict]:
    visible = bundle_visible_text(note)
    extract_text = bundle_extract_text(note)
    relevance = classify_relevance(extract_text)
    rows = extract_opportunities(extract_text)
    out: list[dict] = []
    for row in rows:
        school = normalize_school(row.school_claimed or "")
        contact = classify_contact(visible)
        kind = classify_source_kind(
            visible_text=visible,
            pi_name=row.pi_name,
            school_claimed=row.school_claimed,
            school_resolvable=school is not None,
        )
        verification = verify_school(
            row.school_claimed,
            homepage_text=note.get("homepage_text"),
            homepage_url=row.homepage_url or note.get("homepage_url"),
            openalex_affiliations=note.get("openalex_affiliations"),
        )
        record = {
            "pi_name": row.pi_name,
            "name": row.pi_name,
            "school_claimed": row.school_claimed or "",
            "school_canonical": verification.school_canonical,
            "school_country": verification.school_country,
            "school_status": verification.school_status,
            "school_evidence": [
                {
                    "source": e.source,
                    "url": e.url,
                    "snippet": e.snippet,
                    "fetched_at": e.fetched_at,
                }
                for e in verification.evidence
            ],
            "suggested_school": verification.suggested_school,
            "homepage_url": row.homepage_url,
            "research_areas": row.research_areas,
            "research_topics": row.research_topics,
            "opportunity_types": row.opportunity_types or ["other"],
            "types": row.opportunity_types or ["other"],
            "start_term": row.start_term,
            "excerpt": row.excerpt,
            "email": row.email,
            "contact": row.email or row.homepage_url,
            "contact_class": contact,
            "source": {
                "source": note.get("source") or "xhs",
                "source_kind": kind,
                "url": note.get("source_url") or "",
                "note_id": note.get("note_id"),
                "title": note.get("title") or "",
            },
            "source_kind": kind,
            "relevance": relevance,
            "extract_confidence": row.extract_confidence,
            "updated_at": note.get("updated_at") or note.get("posted_at") or "2026-08-01",
            "listable": (
                relevance == "cs"
                and should_list_source(kind, contact)
                and is_main_table_name(row.pi_name)
            ),
        }
        out.append(record)
    return out


def write_outputs(merged, listings_path: Path, pis_dir: Path) -> dict:
    ensure_dirs()
    pis_dir.mkdir(parents=True, exist_ok=True)
    listings = []
    keep_pis: set[str] = set()
    for item in merged:
        rec = item.records[0]
        if not rec.get("listable"):
            continue
        pi_id = _slug(item.name, item.school_canonical)
        topics: list[str] = []
        for row in item.records:
            for topic in row.get("research_topics") or []:
                if topic and topic not in topics:
                    topics.append(topic)
        detail = {
            "pi_id": pi_id,
            "name": item.name,
            "name_en": None,
            "school_claimed": rec.get("school_claimed") or "",
            "school_canonical": item.school_canonical,
            "school_country": item.school_country,
            "school_status": item.school_status,
            "school_evidence": rec.get("school_evidence") or [],
            "suggested_school": rec.get("suggested_school"),
            "homepage_url": item.homepage_url,
            "research_areas": item.research_areas,
            "research_topics": topics,
            "updated_at": rec.get("updated_at"),
            "opportunities": [
                {
                    "opportunity_id": f"{pi_id}-{i}",
                    "pi_id": pi_id,
                    "types": r.get("opportunity_types") or ["other"],
                    "start_term": r.get("start_term"),
                    "excerpt": r.get("excerpt") or "",
                    "research_topics": r.get("research_topics") or [],
                    "email": r.get("email"),
                    "contact": r.get("contact"),
                    "contact_class": r.get("contact_class"),
                    "source": (r.get("source") or {}).get("source") or "xhs",
                    "source_kind": (r.get("source") or {}).get("source_kind") or "unknown",
                    "source_url": (r.get("source") or {}).get("url") or "",
                    "source_title": (r.get("source") or {}).get("title") or "",
                    "source_note_id": (r.get("source") or {}).get("note_id"),
                    "posted_at": r.get("updated_at"),
                    "collected_at": datetime.now(timezone.utc).date().isoformat(),
                    "relevance": r.get("relevance"),
                    "extract_confidence": r.get("extract_confidence"),
                }
                for i, r in enumerate(item.records)
            ],
        }
        (pis_dir / f"{pi_id}.json").write_text(
            json.dumps(detail, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        keep_pis.add(f"{pi_id}.json")
        listings.append(
            {
                "pi_id": pi_id,
                "name": item.name,
                "name_en": None,
                "school_canonical": item.school_canonical,
                "school_country": item.school_country,
                "school_status": item.school_status,
                "research_areas": item.research_areas,
                "opportunity_types": item.opportunity_types,
                "start_term": rec.get("start_term"),
                "source_count": len(item.records),
                "updated_at": rec.get("updated_at"),
                "detail_path": f"pis/{pi_id}.html",
                "suggested_school": rec.get("suggested_school"),
            }
        )
    listings.sort(key=lambda row: row.get("updated_at") or "", reverse=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).date().isoformat(),
        "listings": listings,
    }
    listings_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    for path in pis_dir.glob("*.json"):
        if path.name not in keep_pis:
            path.unlink()
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=BUNDLES_DIR)
    parser.add_argument("--listings", type=Path, default=LISTINGS_PATH)
    parser.add_argument("--pis-dir", type=Path, default=PIS_DIR)
    parser.add_argument("--audit", type=Path, default=AUDIT_PATH)
    args = parser.parse_args(argv)
    notes = load_notes(args.input_dir)
    records: list[dict] = []
    for note in notes:
        records.extend(process_note(note))
    audit = write_audit(records, args.audit)
    merged = merge_records(records)
    write_outputs(merged, args.listings, args.pis_dir)
    listed = len(json.loads(args.listings.read_text(encoding="utf-8"))["listings"])
    print(
        f"Wrote {args.listings} ({listed} listings); "
        f"audit {args.audit} dropped={audit['counts']['dropped']} agency={audit['counts']['agency']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
