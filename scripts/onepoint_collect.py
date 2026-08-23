#!/usr/bin/env python3
"""Collect 1point3acres fid=173 threads. Offline fixtures first; live stops on Cloudflare."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from _paths import RAW_1P3A
from onepoint_parse import FORUM_BASE, parse_forum_list, parse_thread, thread_to_note

FORUM_FID = 173
FORUM_LIST_URL = f"{FORUM_BASE}forum-{FORUM_FID}-1.html"
USER_AGENT = (
    "Mozilla/5.0 (compatible; CS-PhD-Hiring/0.1; +https://github.com/null1024-ws/CS-PhD-Hiring)"
)
BLOCK_MARKERS = (
    "just a moment",
    "cf-browser-verification",
    "challenge-platform",
    "attention required",
    "cf-challenge",
    "请稍候",
)


def _prefer_local_playwright_browsers() -> None:
    """Cursor sandboxes remap PLAYWRIGHT_BROWSERS_PATH; use a real local install if empty."""
    mapped = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if mapped and Path(mapped, "chromium-1161", "chrome-win", "chrome.exe").is_file():
        return
    local = Path.home() / "AppData" / "Local" / "ms-playwright"
    if (local / "chromium-1161" / "chrome-win" / "chrome.exe").is_file():
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(local)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _is_challenge_tab(url: str, title: str, html: str) -> bool:
    title_l = (title or "").lower()
    url_l = (url or "").lower()
    if 'id="threadlist"' in (html or "") or "normalthread_" in (html or ""):
        return False
    if "just a moment" in title_l or "请稍候" in (title or ""):
        return True
    if "cdn-cgi" in url_l or "challenges.cloudflare" in url_l:
        return True
    if title and "请稍候" not in title and "just a moment" not in title_l:
        if "1point3acres" in url_l or "/bbs" in url_l:
            return False
    return looks_blocked(html or "") == "cloudflare"


def looks_blocked(html: str, status: int = 200) -> str | None:
    body = html or ""
    if (
        'id="threadlist"' in body
        or "normalthread_" in body
        or 'id="postmessage_' in body
        or 'id="thread_subject"' in body
        or 'class="s xst"' in body
    ):
        return None
    if status in (401, 403, 429, 503):
        return "cloudflare" if status in (403, 503) else "blocked"
    text = body.lower()
    if any(marker in text for marker in BLOCK_MARKERS) or "请稍候" in body:
        return "cloudflare"
    if "captcha" in text or "验证码" in body:
        return "captcha"
    return None


def fetch_page(url: str, timeout: float = 20.0) -> dict:
    """Live GET. Tests monkeypatch this. Never used by --from-dir."""
    try:
        import httpx
    except ImportError:
        return {"error": "not_configured", "message": "httpx not installed", "url": url}
    try:
        response = httpx.get(
            url,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
            timeout=timeout,
        )
    except Exception as exc:  # noqa: BLE001 — collector must stop, not crash
        return {"error": "network", "message": str(exc), "url": url}
    blocked = looks_blocked(response.text, response.status_code)
    if blocked:
        return {"error": blocked, "message": f"{blocked} on {url}", "url": url, "status": response.status_code}
    return {"html": response.text, "status": response.status_code, "url": str(response.url)}


def _free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class UserChromeFetcher:
    """Launch a normal Chrome (no Playwright flags) and only read the tab."""

    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._proc: subprocess.Popen | None = None
        self._playwright = None
        self._browser = None
        self._page = None

    def start(self) -> str | None:
        chrome = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
        if not chrome.is_file():
            return "not_configured"
        profile = RAW_1P3A / ".chrome-user"
        profile.mkdir(parents=True, exist_ok=True)
        port = _free_port()
        self._proc = subprocess.Popen(
            [
                str(chrome),
                f"--remote-debugging-port={port}",
                f"--user-data-dir={profile}",
                "--no-first-run",
                "--no-default-browser-check",
                FORUM_LIST_URL,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        endpoint = f"http://127.0.0.1:{port}"
        for _ in range(40):
            try:
                import httpx

                httpx.get(f"{endpoint}/json/version", timeout=1.0)
                break
            except Exception:
                time.sleep(0.25)
        else:
            return "not_configured"
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        async def _connect() -> None:
            from playwright.async_api import async_playwright

            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.connect_over_cdp(endpoint)
            context = self._browser.contexts[0] if self._browser.contexts else await self._browser.new_context()
            pages = list(context.pages)
            self._page = next(
                (p for p in pages if "1point3acres" in (p.url or "")),
                pages[-1] if pages else await context.new_page(),
            )

        try:
            self._loop.run_until_complete(_connect())
        except Exception as exc:  # noqa: BLE001
            print(f"Could not attach to Chrome: {exc}", file=sys.stderr)
            return "not_configured"
        print(
            "A normal Chrome window opened. Complete the check there once, "
            "then wait until the 招生版 list is visible.",
            flush=True,
        )
        return None

    async def _state(self) -> dict:
        page = self._page
        if page is None:
            return {"url": "", "title": "", "html": ""}
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=8000)
        except Exception:
            pass
        try:
            title = await page.title()
        except Exception:
            title = ""
        try:
            html = await page.content()
        except Exception:
            html = ""
        return {"url": getattr(page, "url", "") or "", "title": title, "html": html}

    async def _goto(self, url: str) -> dict:
        if self._page is None:
            return {"url": "", "title": "", "html": ""}
        try:
            await self._page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except Exception as exc:
            print(f"  navigate failed: {exc}", flush=True)
        return await self._state()

    def get(self, url: str) -> dict:
        assert self._loop and self._page

        def _same(current: str, target: str) -> bool:
            return current.split("?")[0].rstrip("/") == target.split("?")[0].rstrip("/")

        state = self._loop.run_until_complete(self._state())
        html = state.get("html") or ""
        current = state.get("url") or ""
        if _same(current, url) and html and not looks_blocked(html):
            return {"html": html, "url": current}
        if (
            not html
            or looks_blocked(html)
            or _is_challenge_tab(current, state.get("title") or "", html)
        ):
            deadline = time.time() + 300
            last = ""
            while time.time() < deadline:
                time.sleep(3)
                state = self._loop.run_until_complete(self._state())
                html = state.get("html") or ""
                current = state.get("url") or ""
                note = f"{state.get('title') or ''} | {current}"
                if note != last:
                    print(f"  tab: {note}", flush=True)
                    last = note
                if html and not looks_blocked(html):
                    print("Forum page is visible.", flush=True)
                    if _same(current, url):
                        return {"html": html, "url": current}
                    break
                print(f"  waiting… {int(deadline - time.time())}s left", flush=True)
        if html and not looks_blocked(html) and not _same(self._page.url or "", url):
            print(f"  open {url}", flush=True)
            state = self._loop.run_until_complete(self._goto(url))
            html = state.get("html") or ""
            if html and not looks_blocked(html):
                return {"html": html, "url": state.get("url") or url}
        elif html and not looks_blocked(html):
            return {"html": html, "url": current or url}
        return {"error": "cloudflare", "message": f"cloudflare on {url}", "url": url}

    def close(self) -> None:
        async def _stop() -> None:
            if self._playwright:
                await self._playwright.stop()

        if self._loop:
            try:
                self._loop.run_until_complete(_stop())
            except Exception:
                pass
            self._loop.close()
            self._loop = None
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()


class Crawl4aiFetcher:
    """Optional local browser session. Not imported by tests or CI."""

    SESSION_ID = "1p3a-collect"

    def __init__(self, *, headed: bool = False) -> None:
        self.headed = headed
        self._loop: asyncio.AbstractEventLoop | None = None
        self._crawler = None
        self._CacheMode = None
        self._CrawlerRunConfig = None

    def start(self) -> str | None:
        try:
            from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
        except ImportError:
            return "not_configured"
        self._CacheMode = CacheMode
        self._CrawlerRunConfig = CrawlerRunConfig
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        _prefer_local_playwright_browsers()
        chrome = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
        profile = RAW_1P3A / ".browser-profile"
        profile.mkdir(parents=True, exist_ok=True)
        browser = BrowserConfig(
            headless=not self.headed,
            verbose=False,
            chrome_channel="chrome" if chrome.is_file() else "chromium",
            use_persistent_context=self.headed,
            user_data_dir=str(profile) if self.headed else None,
        )
        self._crawler = AsyncWebCrawler(config=browser)
        try:
            self._loop.run_until_complete(self._crawler.start())
        except Exception as exc:  # noqa: BLE001
            print(f"Crawl4AI failed to start: {exc}", file=sys.stderr)
            return "not_configured"
        return None

    def _cfg(self):
        return self._CrawlerRunConfig(
            session_id=self.SESSION_ID,
            cache_mode=self._CacheMode.BYPASS,
            wait_until="domcontentloaded",
            page_timeout=60000,
            delay_before_return_html=1.0,
        )

    def _html_from(self, url: str) -> dict:
        try:
            result = self._loop.run_until_complete(
                self._crawler.arun(url=url, config=self._cfg())
            )
        except Exception as exc:  # noqa: BLE001
            return {"error": "network", "message": str(exc), "url": url}
        html = getattr(result, "html", None) or ""
        if getattr(result, "success", True) is False and not html:
            return {
                "error": "network",
                "message": getattr(result, "error_message", None) or "crawl4ai failed",
                "url": url,
            }
        return {"html": html, "url": url}

    def _page(self):
        manager = self._crawler.crawler_strategy.browser_manager
        sess = manager.sessions.get(self.SESSION_ID)
        return None if not sess else sess[1]

    async def _tab_state(self) -> dict:
        """Read the open tab. Do not navigate — reloads reset the site check."""
        page = self._page()
        if page is None:
            return {"url": "", "title": "", "html": ""}
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=8000)
        except Exception:
            pass
        url = getattr(page, "url", "") or ""
        try:
            title = await page.title()
        except Exception:
            title = ""
        try:
            html = await page.content()
        except Exception:
            html = ""
        return {"url": url, "title": title, "html": html}

    async def _open_forum_once(self) -> dict:
        page = self._page()
        if page is None:
            return {"url": "", "title": "", "html": ""}
        print(f"Opening 招生版 once from {page.url}", flush=True)
        try:
            await page.goto(FORUM_LIST_URL, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_load_state("domcontentloaded", timeout=15000)
        except Exception as exc:
            print(f"  navigate failed: {exc}", flush=True)
        return await self._tab_state()

    def get(self, url: str) -> dict:
        assert self._loop and self._crawler
        fetched = self._html_from(url)
        if fetched.get("error"):
            return fetched
        html = fetched.get("html") or ""
        if not looks_blocked(html):
            return {"html": html, "url": url}
        if not self.headed:
            return {"error": "cloudflare", "message": f"cloudflare on {url}", "url": url}
        print(
            "Keep this Chrome window. Click the check once, then wait. "
            "After the wait page goes away, the script opens 招生版 once.",
            flush=True,
        )
        deadline = time.time() + 180
        opened_forum = False
        last_note = ""
        while time.time() < deadline:
            time.sleep(3)
            state = self._loop.run_until_complete(self._tab_state())
            html = state.get("html") or ""
            tab_url = state.get("url") or ""
            title = state.get("title") or ""
            note = f"{title} | {tab_url}"
            if note != last_note:
                print(f"  tab: {note}", flush=True)
                last_note = note
            if html and not looks_blocked(html):
                print("Thread list appeared.", flush=True)
                return {"html": html, "url": tab_url or url}
            if (not _is_challenge_tab(tab_url, title, html)) and not opened_forum:
                opened_forum = True
                state = self._loop.run_until_complete(self._open_forum_once())
                html = state.get("html") or ""
                if html and not looks_blocked(html):
                    print("Thread list appeared.", flush=True)
                    return {"html": html, "url": state.get("url") or url}
            print(f"  waiting for thread list… {int(deadline - time.time())}s left", flush=True)
        return {"error": "cloudflare", "message": f"cloudflare on {url}", "url": url}

    def close(self) -> None:
        if self._crawler and self._loop:
            try:
                self._loop.run_until_complete(self._crawler.close())
            except Exception:
                pass
        if self._loop:
            self._loop.close()
            self._loop = None


def load_index(path: Path) -> dict:
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"tids": {}, "pages": []}


def save_index(path: Path, index: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")


def thread_html_file(from_dir: Path, tid: str, used_generic: bool) -> tuple[Path | None, bool]:
    for name in (f"thread-{tid}.html", f"thread-{tid}-1-1.html"):
        path = from_dir / name
        if path.is_file():
            return path, used_generic
    generic = from_dir / "thread.html"
    if generic.is_file() and not used_generic:
        return generic, True
    return None, used_generic


def write_thread_outputs(out_dir: Path, row: dict, html: str) -> dict:
    thread = parse_thread(html, url=row.get("url") or "")
    if row.get("posted_at") and not thread.get("posted_at"):
        thread["posted_at"] = row["posted_at"]
    if row.get("tid") and not thread.get("tid"):
        thread["tid"] = row["tid"]
    note = thread_to_note(thread)
    out_dir.mkdir(parents=True, exist_ok=True)
    html_dir = out_dir / "html"
    html_dir.mkdir(parents=True, exist_ok=True)
    (html_dir / f"thread-{note['note_id'].removeprefix('1p3a-')}.html").write_text(html, encoding="utf-8")
    note_path = out_dir / f"{note['note_id']}.json"
    note_path.write_text(json.dumps(note, indent=2, ensure_ascii=False), encoding="utf-8")
    return note


def collect_from_dir(from_dir: Path, out_dir: Path, *, max_threads: int, sleep_s: float, dry_run: bool) -> int:
    list_path = from_dir / "forum_list.html"
    if not list_path.is_file():
        print(f"forum_list.html not found in {from_dir}", file=sys.stderr)
        return 2
    html = list_path.read_text(encoding="utf-8")
    rows = parse_forum_list(html)
    if dry_run:
        for row in rows:
            print(f"{row['tid']}\t{row['title']}\t{row['url']}", flush=True)
        return 0

    index_path = out_dir / "index.json"
    index = load_index(index_path)
    written = 0
    used_generic = False
    (out_dir / "html").mkdir(parents=True, exist_ok=True)
    (out_dir / "html" / "forum-173-1.html").write_text(html, encoding="utf-8")
    for row in rows:
        if written >= max_threads:
            break
        tid = row["tid"]
        if tid in index["tids"]:
            continue
        path, used_generic = thread_html_file(from_dir, tid, used_generic)
        if path is None:
            continue
        note = write_thread_outputs(out_dir, row, path.read_text(encoding="utf-8"))
        index["tids"][tid] = {
            "note_id": note["note_id"],
            "url": note["source_url"],
            "fetched_at": utc_now(),
        }
        save_index(index_path, index)
        written += 1
        if sleep_s:
            time.sleep(sleep_s)
    index["pages"].append({"source": "fixture", "threads": written, "at": utc_now()})
    save_index(index_path, index)
    print(f"Wrote {written} notes under {out_dir}", flush=True)
    return 0


def collect_live(
    out_dir: Path,
    *,
    max_threads: int,
    sleep_s: float,
    dry_run: bool,
    use_browser: bool,
    headed: bool = False,
) -> int:
    if dry_run:
        print(FORUM_LIST_URL, flush=True)
        print(f"max_threads={max_threads}", flush=True)
        return 0

    index_path = out_dir / "index.json"
    existing = index_path.read_text(encoding="utf-8") if index_path.is_file() else None
    page = fetch_page(FORUM_LIST_URL)
    fetcher: Crawl4aiFetcher | None = None
    if page.get("error") in {"cloudflare", "captcha", "blocked"} and use_browser:
        print("httpx blocked; trying a local browser once.", flush=True)
        fetcher = UserChromeFetcher() if headed else Crawl4aiFetcher(headed=False)
        start_err = fetcher.start()
        if start_err:
            print("Crawl4AI not configured. Save forum HTML and use --from-dir.", file=sys.stderr)
            fetcher.close()
            return 2
        page = fetcher.get(FORUM_LIST_URL)
    err = page.get("error")
    if err:
        if fetcher:
            fetcher.close()
        if err == "not_configured":
            print("Browser/HTTP client not configured. Save forum HTML and use --from-dir.", file=sys.stderr)
            return 2
        print(f"Stopped: {page.get('message') or err}. Do not retry against risk control.", file=sys.stderr)
        if existing is not None and index_path.is_file():
            index_path.write_text(existing, encoding="utf-8")
        return 3

    html = page.get("html") or ""
    rows = parse_forum_list(html)
    index = load_index(index_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "html").mkdir(parents=True, exist_ok=True)
    (out_dir / "html" / "forum-173-1.html").write_text(html, encoding="utf-8")
    written = 0
    try:
        for row in rows:
            if written >= max_threads:
                break
            tid = row["tid"]
            if tid in index["tids"]:
                continue
            print(f"  read {tid} {row.get('title') or ''}", flush=True)
            thread_page = fetcher.get(row["url"]) if fetcher else fetch_page(row["url"])
            terr = thread_page.get("error")
            if terr:
                print(f"Stopped on thread {tid}: {thread_page.get('message') or terr}", file=sys.stderr)
                return 3
            note = write_thread_outputs(out_dir, row, thread_page.get("html") or "")
            index["tids"][tid] = {
                "note_id": note["note_id"],
                "url": note["source_url"],
                "fetched_at": utc_now(),
            }
            save_index(index_path, index)
            written += 1
            if sleep_s:
                time.sleep(sleep_s)
    finally:
        if fetcher:
            fetcher.close()
    index["pages"].append({"source": FORUM_LIST_URL, "threads": written, "at": utc_now()})
    save_index(index_path, index)
    print(f"Wrote {written} notes under {out_dir}", flush=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect 1point3acres 招生版 (fid=173)")
    parser.add_argument("--from-dir", type=Path, help="Offline HTML directory (forum_list.html + thread HTML)")
    parser.add_argument("--out-dir", type=Path, default=RAW_1P3A)
    parser.add_argument("--max-threads", type=int, default=5)
    parser.add_argument("--sleep", type=float, default=8.0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--browser",
        action="store_true",
        help="If httpx hits Cloudflare, try Crawl4AI once (local browser). Not used in tests.",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Show the browser window so a Cloudflare wait can finish. Implies --browser.",
    )
    args = parser.parse_args(argv)
    if args.from_dir:
        return collect_from_dir(
            args.from_dir,
            args.out_dir,
            max_threads=args.max_threads,
            sleep_s=args.sleep,
            dry_run=args.dry_run,
        )
    return collect_live(
        args.out_dir,
        max_threads=args.max_threads,
        sleep_s=args.sleep,
        dry_run=args.dry_run,
        use_browser=args.browser or args.headed,
        headed=args.headed,
    )


if __name__ == "__main__":
    raise SystemExit(main())
