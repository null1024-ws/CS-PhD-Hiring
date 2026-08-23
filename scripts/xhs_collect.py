#!/usr/bin/env python3
"""Collect Xiaohongshu hiring notes via xhs-cli. Checkpoint/resume, conservative rate limits."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from _paths import RAW_INDEX, RAW_XHS, ensure_dirs
from search_queries import all_queries


def xhs_bin() -> str:
    return os.environ.get("XHS_BIN", "xhs")


def classify_xhs_error(stderr: str, stdout: str) -> dict:
    text = f"{stderr}\n{stdout}".lower()
    if "not logged in" in text or "not_authenticated" in text:
        return {"_error": "not_authenticated", "message": (stderr or stdout).strip()}
    if "verification" in text or "captcha" in text:
        return {"_error": "verification_required", "message": (stderr or stdout).strip()}
    return {"_error": "fetch_failed", "message": (stderr or stdout).strip()}


def _attach_error(parsed: dict) -> dict:
    if parsed.get("ok") is False:
        blob = json.dumps(parsed, ensure_ascii=False).lower()
        code = str((parsed.get("error") or {}).get("code") or "")
        if code == "not_authenticated" or "not logged" in blob:
            parsed["_error"] = "not_authenticated"
        elif "verif" in blob or "captcha" in blob:
            parsed["_error"] = "verification_required"
        else:
            parsed["_error"] = code or "fetch_failed"
    return parsed


def run_xhs(args: list[str], timeout: int = 240) -> dict | list | None:
    binary = xhs_bin()
    if not shutil.which(binary) and not Path(binary).exists():
        return {"_error": "not_authenticated", "message": "xhs CLI not found. Run: xhs login"}
    cmd = [binary, *args, "--json"]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
        )
        if result.stdout.strip():
            try:
                parsed = json.loads(result.stdout)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, dict):
                return _attach_error(parsed)
            if parsed is not None:
                return parsed
        if result.returncode != 0:
            return classify_xhs_error(result.stderr, result.stdout)
        return None
    except subprocess.TimeoutExpired:
        return {"_error": "fetch_failed", "message": "timeout"}


def payload_of(data: dict | list | None) -> dict | list | None:
    if isinstance(data, dict) and "data" in data and data.get("_error") is None:
        return data.get("data")
    return data


def error_code(data: dict | list | None) -> str | None:
    if isinstance(data, dict):
        return data.get("_error")
    return None


def load_raw_index() -> dict:
    if RAW_INDEX.is_file():
        return json.loads(RAW_INDEX.read_text(encoding="utf-8"))
    return {"notes": {}, "searches": [], "checkpoint": {"completed_searches": []}}


def save_raw_index(index: dict) -> None:
    ensure_dirs()
    RAW_INDEX.parent.mkdir(parents=True, exist_ok=True)
    RAW_INDEX.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")


def note_id_from_item(item: dict) -> str | None:
    for key in ("id", "note_id", "noteId"):
        if item.get(key):
            return str(item[key]).split("#", 1)[0]
    card = item.get("note_card") or item.get("noteCard") or {}
    if card.get("note_id") or card.get("id"):
        return str(card.get("note_id") or card.get("id")).split("#", 1)[0]
    return None


def xsec_from_item(item: dict) -> str:
    card = item.get("note_card") or item.get("noteCard") or {}
    return str(item.get("xsec_token") or item.get("xsecToken") or card.get("xsec_token") or "")


def extract_search_items(data: dict | list | None) -> list[dict]:
    payload = payload_of(data)
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("items", "notes", "note_list"):
            rows = payload.get(key)
            if isinstance(rows, list):
                return [item for item in rows if isinstance(item, dict)]
    return []


def fetch_note(note_id: str, xsec_token: str) -> dict:
    read_args = ["read", note_id]
    if xsec_token:
        read_args.extend(["--xsec-token", xsec_token])
    read_data = run_xhs(read_args, timeout=300)
    comments_data = None
    if error_code(read_data) is None:
        comment_args = ["comments", note_id]
        if xsec_token:
            comment_args.extend(["--xsec-token", xsec_token])
        comments_data = run_xhs(comment_args, timeout=180)
    return {
        "note_id": note_id,
        "fetched_at": time.time(),
        "read": read_data,
        "comments": comments_data,
        "note": payload_of(read_data) if isinstance(payload_of(read_data), dict) else {},
        "comment_error": error_code(comments_data),
        "read_error": error_code(read_data),
    }


def fetch_authenticated() -> dict | list | None:
    return run_xhs(["status"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect XHS CS hiring posts")
    parser.add_argument("--max-notes", type=int, default=20)
    parser.add_argument("--sleep", type=float, default=10.0)
    parser.add_argument("--note-sleep", type=float, default=3.0)
    parser.add_argument("--query", action="append", dest="queries")
    parser.add_argument("--force", action="store_true", help="re-run a query even if completed")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    ensure_dirs()
    index = load_raw_index()
    probe = fetch_authenticated()
    err = error_code(probe) or ""
    if isinstance(probe, dict) and probe.get("ok") is False and not err:
        err = "not_authenticated"
    if err == "not_authenticated":
        print("Not authenticated. Run: xhs login", file=sys.stderr, flush=True)
        return 2
    if err == "verification_required":
        print("Verification required. Re-login with `xhs login`.", file=sys.stderr, flush=True)
        return 3

    if args.dry_run:
        print("\n".join(all_queries()), flush=True)
        return 0

    completed = index["checkpoint"].setdefault("completed_searches", [])
    total_new = 0
    for query in args.queries or all_queries():
        if query in completed and not args.force:
            print(f" skip (done): {query}", flush=True)
            continue
        print(f" search: {query}", flush=True)
        data = run_xhs(["search", query])
        code = error_code(data)
        if code == "not_authenticated":
            print("Not authenticated. Run: xhs login", file=sys.stderr)
            return 2
        if code == "verification_required":
            print("Verification required. Stop to avoid risk control.", file=sys.stderr)
            return 3
        items = extract_search_items(data)
        new_notes = 0
        for item in items:
            if new_notes >= args.max_notes:
                break
            note_id = note_id_from_item(item)
            if not note_id:
                continue
            if note_id in index["notes"]:
                queries = index["notes"][note_id].setdefault("queries", [])
                if query not in queries:
                    queries.append(query)
                continue
            print(f"  read {note_id}", flush=True)
            bundle = fetch_note(note_id, xsec_from_item(item))
            if bundle.get("read_error") == "not_authenticated":
                print("Not authenticated. Run: xhs login", file=sys.stderr)
                return 2
            if bundle.get("read_error") == "verification_required":
                print("Verification required. Stop to avoid risk control.", file=sys.stderr)
                return 3
            bundle["search_query"] = query
            bundle["search_item"] = item
            (RAW_XHS / f"{note_id}.json").write_text(
                json.dumps(bundle, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            index["notes"][note_id] = {
                "query": query,
                "queries": [query],
                "fetched_at": bundle["fetched_at"],
            }
            new_notes += 1
            total_new += 1
            save_raw_index(index)
            time.sleep(args.note_sleep)
        if query not in completed:
            completed.append(query)
        index["searches"].append(
            {"query": query, "items_found": len(items), "new_notes": new_notes, "at": time.time()}
        )
        save_raw_index(index)
        print(f" new={new_notes}", flush=True)
        time.sleep(args.sleep)
    print(f"Done. {total_new} new notes. Total stored: {len(index['notes'])}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
