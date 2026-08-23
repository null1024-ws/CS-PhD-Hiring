"""Detect research-agency posts. Tone is ignored; contact in body+OCR is the signal."""

from __future__ import annotations

import re

from extract import EMAIL_RE, URL_RE, SKIP_URL_HOST, clean_url, is_weak_pi_name

EXPLICIT_AGENCY_RE = re.compile(
    r"代申|中介|包\s*offer|文书全程|选校定位|申请辅导|保录取|"
    r"帮你避坑|别再海投|针对性套磁|留学中介|我帮你(?:改|看|避)",
    re.I,
)
SOCIAL_RE = re.compile(
    r"私信|加微信|加\s*vx|微信|评论区扣|扣\s*1|看主页私|踢我|滴我|勾搭我",
    re.I,
)
PITCH_RE = re.compile(r"推荐.{0,10}老师组|来看看.{0,16}导师组")
CONSUMER_HOST_RE = re.compile(
    r"@(?:gmail|qq|163|126|outlook|hotmail|yahoo)\.",
    re.I,
)
EDU_EMAIL_RE = re.compile(
    r"@[A-Z0-9.-]+\.(?:edu|ac\.[a-z]{2,}|edu\.[a-z]{2,})(?:\.[a-z]{2})?\b",
    re.I,
)
UNI_EMAIL_RE = re.compile(
    r"@(?:ust\.hk|cuhk\.edu\.hk|hku\.hk|cityu\.edu\.hk|polyu\.edu\.hk|"
    r"nus\.edu\.sg|ntu\.edu\.sg|mit\.edu|stanford\.edu)",
    re.I,
)


def classify_contact(visible_text: str) -> str:
    """Classify contact using title+body+OCR only. Do not pass comments here."""
    text = visible_text or ""
    emails = EMAIL_RE.findall(text)
    urls = [
        url
        for url in (clean_url(u) for u in URL_RE.findall(text))
        if url and not SKIP_URL_HOST.search(url)
    ]
    if any(EDU_EMAIL_RE.search(e) or UNI_EMAIL_RE.search(e) for e in emails) or urls:
        return "academic"
    if emails and any(CONSUMER_HOST_RE.search(e) for e in emails):
        return "consumer_email"
    if SOCIAL_RE.search(text):
        return "social_only"
    return "none"


def classify_source_kind(
    *,
    visible_text: str,
    pi_name: str,
    school_claimed: str | None,
    school_resolvable: bool,
) -> str:
    text = visible_text or ""
    if EXPLICIT_AGENCY_RE.search(text):
        return "agency"

    contact = classify_contact(text)
    if contact != "academic" and PITCH_RE.search(text):
        return "agency"
    has_pi = bool(pi_name) and not is_weak_pi_name(pi_name) and bool(school_claimed)
    if contact == "academic":
        return "pi"
    if contact == "consumer_email":
        return "unknown"
    if contact == "social_only":
        return "agency"
    if has_pi and school_resolvable:
        return "repost"
    return "unknown"


def should_list_source(source_kind: str, contact_class: str) -> bool:
    if source_kind == "agency":
        return False
    if contact_class == "consumer_email" or source_kind == "unknown":
        return False
    return source_kind in {"pi", "repost"}
