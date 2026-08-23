#!/usr/bin/env python3
"""Import a GitHub Issue body into a pipeline note. School is never auto-verified."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from _paths import BUNDLES_DIR, ensure_dirs

FIELD_RE = re.compile(r"^-\s+\*\*(.+?)\*\*[：:]\s*(.*)$")
HEADING_RE = re.compile(r"^#{1,3}\s+(.+)$")


def parse_issue(body: str) -> dict:
    fields: dict[str, str] = {}
    heading: str | None = None
    buf: list[str] = []

    def flush() -> None:
        nonlocal heading
        if heading:
            fields[heading] = " ".join(buf).strip()
        heading = None
        buf.clear()

    for line in body.splitlines():
        match = FIELD_RE.match(line.strip())
        if match:
            flush()
            fields[match.group(1).strip()] = match.group(2).strip()
            continue
        head = HEADING_RE.match(line.strip())
        if head:
            flush()
            heading = head.group(1).strip()
            continue
        if heading:
            buf.append(line.strip())
    flush()
    name = fields.get("导师") or fields.get("name") or "未知"
    school = fields.get("学校") or fields.get("school") or ""
    areas = fields.get("方向") or fields.get("areas") or ""
    types = fields.get("机会类型") or fields.get("types") or "PhD"
    url = fields.get("原帖链接") or fields.get("url") or ""
    extra = fields.get("补充") or ""
    desc = f"{name}教授（{school}）招收 {types}。方向：{areas}。{extra}".strip()
    return {
        "note_id": fields.get("note_id") or "github-import",
        "source": "github",
        "source_url": url,
        "updated_at": fields.get("日期") or "2026-08-01",
        "title": f"{name} {school}",
        "desc": desc,
        "ocr_text": "",
        "comments": [],
        "homepage_text": "",
        "homepage_url": fields.get("主页") or "",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--issue-file", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, default=BUNDLES_DIR)
    args = parser.parse_args(argv)
    note = parse_issue(args.issue_file.read_text(encoding="utf-8"))
    ensure_dirs()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    dest = args.out_dir / f"{note['note_id']}.json"
    dest.write_text(json.dumps(note, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
