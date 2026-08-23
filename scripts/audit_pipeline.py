"""Summarize what the pipeline listed, dropped, and still looks risky."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from _paths import AUDIT_PATH
from extract import is_main_table_name


def drop_reason(record: dict) -> str | None:
    if record.get("listable"):
        return None
    if record.get("relevance") != "cs":
        return str(record.get("relevance") or "notcs")
    if record.get("source_kind") == "agency":
        return "agency"
    if not is_main_table_name(record.get("pi_name") or record.get("name") or ""):
        return "weak_name"
    if record.get("source_kind") == "unknown":
        return "unknown"
    if record.get("contact_class") == "consumer_email":
        return "consumer_email"
    return "not_listable"


def _row(record: dict) -> dict:
    source = record.get("source") or {}
    return {
        "note_id": source.get("note_id") or "",
        "title": source.get("title") or "",
        "name": record.get("name") or record.get("pi_name") or "",
        "school": record.get("school_canonical") or record.get("school_claimed") or "",
        "source_kind": record.get("source_kind") or "",
        "relevance": record.get("relevance") or "",
        "contact_class": record.get("contact_class") or "",
        "listable": bool(record.get("listable")),
        "source_url": source.get("url") or "",
        "topics": record.get("research_topics") or [],
        "reason": drop_reason(record),
    }


def _warnings(record: dict) -> list[str]:
    flags: list[str] = []
    source = record.get("source") or {}
    url = source.get("url") or ""
    if record.get("listable") and "xiaohongshu.com" in url and "xsec_token=" not in url:
        flags.append("source_url_missing_token")
    topics = record.get("research_topics") or []
    excerpt = record.get("excerpt") or ""
    if record.get("listable") and not topics and len(excerpt) > 180:
        flags.append("excerpt_still_a_paragraph")
    if record.get("listable") and record.get("source_kind") == "repost" and not url:
        flags.append("repost_without_url")
    return flags


def build_audit(records: list[dict]) -> dict:
    listed = [_row(r) for r in records if r.get("listable")]
    dropped = [_row(r) for r in records if not r.get("listable")]
    warnings = []
    for record in records:
        for flag in _warnings(record):
            warnings.append({**_row(record), "flag": flag})
    return {
        "generated_at": datetime.now(timezone.utc).date().isoformat(),
        "counts": {
            "records": len(records),
            "listed": len(listed),
            "dropped": len(dropped),
            "warnings": len(warnings),
            "agency": sum(1 for r in dropped if r.get("reason") == "agency"),
            "weak_name": sum(1 for r in dropped if r.get("reason") == "weak_name"),
            "by_reason": {
                reason: sum(1 for r in dropped if r.get("reason") == reason)
                for reason in sorted({r.get("reason") or "not_listable" for r in dropped})
            },
        },
        "listed": listed,
        "dropped": dropped,
        "warnings": warnings,
    }


def write_audit(records: list[dict], path: Path | None = None) -> dict:
    payload = build_audit(records)
    out = path or AUDIT_PATH
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload
