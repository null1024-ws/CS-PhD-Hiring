"""Merge title, body, useful comments, and OCR into extractable text."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

USEFUL_COMMENT_RE = re.compile(
    r"@|邮箱|email|主页|http|截止|ddl|更正|学校|教授",
    re.I,
)
QUESTION_COMMENT_RE = re.compile(r"有了解|求问|同问|插眼|\+1|蹲|请问", re.I)


def _comment_text(comment: Any) -> str:
    if isinstance(comment, str):
        return comment
    if isinstance(comment, dict):
        return str(comment.get("content") or comment.get("text") or "")
    return ""


def useful_comments(comments: list[Any] | None) -> list[str]:
    kept: list[str] = []
    for comment in comments or []:
        text = _comment_text(comment).strip()
        if not text:
            continue
        if QUESTION_COMMENT_RE.search(text) and not USEFUL_COMMENT_RE.search(text):
            continue
        if USEFUL_COMMENT_RE.search(text):
            kept.append(text)
    return kept


def bundle_visible_text(note: dict) -> str:
    """Title + body + OCR. Comments are excluded (agency rule)."""
    parts = [
        note.get("title") or "",
        note.get("desc") or note.get("content") or "",
        note.get("ocr_text") or "",
    ]
    return "\n".join(p for p in parts if p).strip()


def flatten_collected_note(raw: dict) -> dict:
    """Accept fixture notes or xhs-cli raw bundles."""
    if raw.get("title") or raw.get("desc") or raw.get("source") == "github":
        return raw
    note = raw.get("note") if isinstance(raw.get("note"), dict) else {}
    if "title" not in note and "desc" not in note and isinstance(note.get("note"), dict):
        note = note["note"]
    read = raw.get("read") if isinstance(raw.get("read"), dict) else {}
    read_data = read.get("data") if isinstance(read.get("data"), dict) else {}
    items = note.get("items") if isinstance(note.get("items"), list) else read_data.get("items")
    if isinstance(items, list) and items and isinstance(items[0], dict):
        card = items[0].get("note_card") or items[0].get("noteCard") or {}
        if card:
            note = {**card, **note}
    search = raw.get("search_item") if isinstance(raw.get("search_item"), dict) else {}
    card = search.get("note_card") or search.get("noteCard") or {}
    title = (
        note.get("title")
        or note.get("display_title")
        or card.get("display_title")
        or card.get("title")
        or ""
    )
    desc = note.get("desc") or note.get("description") or card.get("desc") or ""
    note_id = str(raw.get("note_id") or note.get("note_id") or note.get("id") or search.get("id") or "")
    comments = raw.get("comments") or []
    if isinstance(comments, dict):
        inner = comments.get("data") if isinstance(comments.get("data"), dict) else comments
        comments = inner.get("comments") or inner.get("data") or []
    time_val = note.get("time") or note.get("last_update_time") or note.get("timestamp")
    updated = raw.get("updated_at") or ""
    if not updated and time_val:
        try:
            ts = int(time_val)
            if ts > 10**12:
                ts //= 1000
            updated = datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
        except (TypeError, ValueError, OSError):
            updated = ""
    url = raw.get("url") or raw.get("source_url") or ""
    if not url and note_id:
        url = f"https://www.xiaohongshu.com/explore/{note_id}"
    return {
        "note_id": note_id,
        "source": "xhs",
        "source_url": url,
        "title": title,
        "desc": desc,
        "comments": comments if isinstance(comments, list) else [],
        "ocr_text": raw.get("ocr_text") or "",
        "updated_at": updated,
    }


def bundle_extract_text(note: dict) -> str:
    """Visible text plus comments that look like hiring corrections."""
    visible = bundle_visible_text(note)
    extra = "\n".join(useful_comments(note.get("comments")))
    return "\n".join(p for p in (visible, extra) if p).strip()
