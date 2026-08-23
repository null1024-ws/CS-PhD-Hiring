"""Parse 1point3acres 招生版 HTML into pipeline notes. No network."""

from __future__ import annotations

import re
from datetime import datetime
from html import unescape
from html.parser import HTMLParser
from urllib.parse import parse_qs, urljoin, urlparse

FORUM_BASE = "https://www.1point3acres.com/bbs/"
THREAD_HREF_RE = re.compile(r"thread-(\d+)-\d+-\d+\.html", re.I)
TID_QUERY_RE = re.compile(r"(?:^|[?&])tid=(\d+)", re.I)
DATE_RE = re.compile(r"(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})")
SKIP_HREF_RE = re.compile(r"javascript:|mod=forumdisplay|mod=faq|mod=help", re.I)


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self._href = href
            self._chunks = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._chunks.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href is not None:
            self.links.append((self._href, "".join(self._chunks)))
            self._href = None


class _FragmentParser(HTMLParser):
    """Collect text inside the first tag with a given id."""

    def __init__(self, target_id: str) -> None:
        super().__init__(convert_charrefs=True)
        self.target_id = target_id
        self.text = ""
        self._depth = 0
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_d = dict(attrs)
        if self._depth:
            self._depth += 1
            return
        if attrs_d.get("id") == self.target_id:
            self._depth = 1
            self._chunks = []

    def handle_data(self, data: str) -> None:
        if self._depth:
            self._chunks.append(data)

    def handle_endtag(self, tag: str) -> None:
        if not self._depth:
            return
        self._depth -= 1
        if self._depth == 0 and not self.text:
            self.text = unescape("".join(self._chunks)).strip()


def _tid_from_href(href: str) -> str | None:
    match = THREAD_HREF_RE.search(href)
    if match:
        return match.group(1)
    parsed = urlparse(href)
    query = parse_qs(parsed.query)
    if query.get("tid"):
        return str(query["tid"][0])
    match = TID_QUERY_RE.search(href)
    return match.group(1) if match else None


def _abs_url(href: str, base: str = FORUM_BASE) -> str:
    href = unescape(href).strip()
    if href.startswith("//"):
        return "https:" + href
    return urljoin(base, href)


def _normalize_date(text: str) -> str | None:
    match = DATE_RE.search(text or "")
    if not match:
        return None
    year, month, day = match.group(1), match.group(2), match.group(3)
    try:
        return datetime(int(year), int(month), int(day)).date().isoformat()
    except ValueError:
        return None


def parse_forum_list(html: str, *, base: str = FORUM_BASE) -> list[dict]:
    """Thread cards from a fid=173 list page. Skip board/faq/javascript links."""
    parser = _LinkParser()
    parser.feed(html or "")
    rows: list[dict] = []
    seen: set[str] = set()
    for href, title in parser.links:
        title = unescape(re.sub(r"\s+", " ", title)).strip()
        if not title or SKIP_HREF_RE.search(href):
            continue
        tid = _tid_from_href(href)
        if not tid or tid in seen:
            continue
        seen.add(tid)
        start = html.find(href)
        if start < 0:
            start = html.find(tid)
        window = html[max(0, start) : start + 500] if start >= 0 else ""
        rows.append(
            {
                "tid": tid,
                "title": title,
                "url": _abs_url(href, base),
                "posted_at": _normalize_date(window),
            }
        )
    return rows


def parse_thread(html: str, *, url: str = "") -> dict:
    """First-post body from a Discuz thread page."""
    subject = _FragmentParser("thread_subject")
    subject.feed(html or "")
    title = re.sub(r"\s+", " ", subject.text).strip()
    if not title:
        match = re.search(r"<title>([^<]+)</title>", html or "", re.I)
        title = unescape(match.group(1)).strip() if match else ""

    body = ""
    match = re.search(r'id="(postmessage_\d+)"', html or "")
    if match:
        fragment = _FragmentParser(match.group(1))
        fragment.feed(html or "")
        body = re.sub(r"\s+", " ", fragment.text).strip()

    tid = _tid_from_href(url) or ""
    if not tid:
        match = re.search(r'tid=(\d+)|thread-(\d+)-', url or html or "")
        tid = (match.group(1) or match.group(2)) if match else ""
    return {
        "tid": tid,
        "title": title,
        "desc": body,
        "url": url or (f"{FORUM_BASE}thread-{tid}-1-1.html" if tid else ""),
        "posted_at": _normalize_date(html or ""),
    }


def thread_to_note(thread: dict) -> dict:
    tid = str(thread.get("tid") or "").strip()
    url = thread.get("url") or ""
    if tid and "1point3acres.com" not in url:
        url = _abs_url(url or f"thread-{tid}-1-1.html")
    return {
        "note_id": f"1p3a-{tid}" if tid else "1p3a-unknown",
        "source": "1p3a",
        "source_url": url,
        "title": thread.get("title") or "",
        "desc": thread.get("desc") or "",
        "updated_at": thread.get("posted_at") or "",
        "comments": [],
        "ocr_text": "",
    }
