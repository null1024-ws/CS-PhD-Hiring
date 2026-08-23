"""Rule-based extraction of hiring opportunities from plain text."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from _paths import SCHOOLS_PATH

OPPORTUNITY_TYPES = ("phd", "ra", "intern", "postdoc", "mres", "visiting")

TYPE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("phd", re.compile(r"\bph\.?d\b|博士|直博|春博|秋博", re.I)),
    ("intern", re.compile(r"\bintern(?:ship)?\b|实习|暑研", re.I)),
    ("ra", re.compile(r"\bra\b|研究助理", re.I)),
    ("postdoc", re.compile(r"\bpost-?doc\b|博后|博士后", re.I)),
    ("mres", re.compile(r"\bmres\b|\bmphil\b|科研硕士", re.I)),
    ("visiting", re.compile(r"\bvisiting\b|访问学[生者]", re.I)),
]

AREA_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("nlp", re.compile(r"\bnlp\b|自然语言|大语言模型|\bllm\b", re.I)),
    ("computer vision", re.compile(r"\bcv\b|计算机视觉|视觉", re.I)),
    ("systems", re.compile(r"\bmlsys\b|系统|systems", re.I)),
    ("security", re.compile(r"安全|\bsecurity\b", re.I)),
    ("hci", re.compile(r"\bhci\b|人机交互", re.I)),
    ("robotics", re.compile(r"机器人|\brobotics\b", re.I)),
    ("ml", re.compile(r"机器学习|深度学习|machine learning", re.I)),
]

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
URL_RE = re.compile(r"https?://[^\s)）,\"']+", re.I)
SKIP_URL_HOST = re.compile(r"xiaohongshu\.com|xhslink\.com|weixin\.qq\.com", re.I)

CN_NAMED_RE = re.compile(
    r"([\u4e00-\u9fff]{1,4})(?:助理教授|副教授|教授|老师)"
)
EN_TITLED_RE = re.compile(
    r"(?:Prof\.?|Dr\.?|Professor)\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){1,2})"
)
SELF_EN_RE = re.compile(
    r"(?:我是|我叫)\s*([A-Z][A-Za-z]+(?:[\s\-]+[A-Z][A-Za-z]+){1,3})"
)
SELF_CN_RE = re.compile(
    r"(?:我是|我叫)\s*([\u4e00-\u9fff]{2,4})(?=[，。！!,\s]|目前|即将|老师|教授|$)"
)
I_AM_RE = re.compile(
    r"\bI(?:'m| am)\s+([A-Z][A-Za-z]+(?:[\s\-]+[A-Z][A-Za-z]+){1,3})"
)
CN_EN_PAIR_RE = re.compile(
    r"(?:^|[^\u4e00-\u9fff]|[和与及、，]|教授|老师|副教授|助理教授)"
    r"([\u4e00-\u9fff]{2,3})"
    r"(?:助理教授|副教授|教授|老师)?"
    r"\s*[（(]\s*(?:Prof\.?|Dr\.?|Professor)?\s*"
    r"([A-Z][A-Za-z.\-]+(?:\s+[A-Z][A-Za-z.\-]+)+)\s*[)）]"
)
ADVISOR_BEFORE_RE = re.compile(r"(师从|指导下|毕业于|此前|曾在)")
HIRE_SCHOOL_RE = re.compile(
    r"(?:即将加入|将加入|会加入|现已加入|入职|现任)\s*([^。\n]{2,80})"
)
PAST_AFFILIATION_RE = re.compile(r"(?:目前在|师从|毕业于|此前|曾在)[^。\n]*")
SELF_SKIP = {"学生", "楼主", "本人", "老师", "作者", "招生"}
WEAK_NAME_RE = re.compile(r"^(?:未知|老师|教授|[\u4e00-\u9fff]老师)$")
NAME_NOISE_RE = re.compile(
    r"教授|老师|助理|讲席|担任|研究所|听过|科学系|特聘|校长|教研|接发|荐麻|等教授|美轨|美籍|华裔|课题|实验室"
)

TERM_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(20\d{2})\s*(Fall|Spring|Summer|Autumn)", re.I),
    re.compile(r"(20\d{2})\s*(秋|春|夏)(?:季|天)?", re.I),
    re.compile(r"\b(\d{2})\s*fall\b", re.I),
    re.compile(r"(春博|秋博|暑研)"),
]


@dataclass
class ExtractedOpportunity:
    pi_name: str
    school_claimed: str | None
    opportunity_types: list[str]
    start_term: str | None
    email: str | None
    homepage_url: str | None
    research_areas: list[str]
    extract_confidence: str
    excerpt: str
    extras: dict = field(default_factory=dict)


def is_weak_pi_name(name: str) -> bool:
    return not name or bool(WEAK_NAME_RE.fullmatch(name.strip()))


def is_main_table_name(name: str) -> bool:
    """Main table hides 张老师 / 未知 and other weak names."""
    name = (name or "").strip()
    if is_weak_pi_name(name) or NAME_NOISE_RE.search(name):
        return False
    if re.match(r"^(从|在|于|地|有|据|任|接)", name):
        return False
    if re.fullmatch(r"[\u4e00-\u9fff]+", name):
        return 2 <= len(name) <= 4
    return bool(re.fullmatch(r"[A-Za-z][A-Za-z.\-]+(?:\s+[A-Za-z][A-Za-z.\-]+)+", name))


@lru_cache(maxsize=1)
def _alias_list(path: str) -> list[str]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    aliases = [alias for row in payload["schools"] for alias in row["aliases"]]
    return sorted(set(aliases), key=len, reverse=True)


def find_claimed_school(text: str, *, schools_path: Path | None = None) -> str | None:
    """Longest alias that appears in the text. Short ASCII aliases need word boundaries."""
    aliases = _alias_list(str(schools_path or SCHOOLS_PATH))
    for alias in aliases:
        if re.search(r"[A-Za-z]", alias) and len(alias) <= 5:
            if re.search(rf"(?<![\w.]){re.escape(alias)}(?![\w.])", text, re.I):
                return alias
        elif alias in text or alias.lower() in text.lower():
            return alias
    return None


def find_hiring_school(text: str, *, schools_path: Path | None = None) -> str | None:
    """Prefer the school the PI is joining or now at, not a past advisor's lab."""
    path = schools_path
    for match in HIRE_SCHOOL_RE.finditer(text):
        school = find_claimed_school(match.group(1), schools_path=path)
        if school:
            return school
    head = text.split("\n", 1)[0]
    school = find_claimed_school(head, schools_path=path)
    if school:
        return school
    stripped = PAST_AFFILIATION_RE.sub(" ", text)
    return find_claimed_school(stripped, schools_path=path) or find_claimed_school(
        text, schools_path=path
    )


def _emails(text: str) -> list[str]:
    return EMAIL_RE.findall(text)


def _homepage(text: str) -> str | None:
    for match in URL_RE.findall(text):
        url = match.rstrip("。．.,，")
        if not SKIP_URL_HOST.search(url):
            return url
    return None


def _types(text: str) -> list[str]:
    found: list[str] = []
    for key, pattern in TYPE_PATTERNS:
        if pattern.search(text) and key not in found:
            found.append(key)
    return found


def _areas(text: str) -> list[str]:
    found: list[str] = []
    for key, pattern in AREA_PATTERNS:
        if pattern.search(text) and key not in found:
            found.append(key)
    return found


def _start_term(text: str) -> str | None:
    season = {"秋": "Fall", "春": "Spring", "夏": "Summer"}
    for pattern in TERM_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        if not match.lastindex:
            continue
        if match.lastindex == 1:
            token = match.group(1)
            if token in {"春博", "秋博", "暑研"}:
                return token
            if token.isdigit() and len(token) == 2:
                return f"20{token} Fall"
            continue
        year, rest = match.group(1), match.group(2)
        if len(year) == 2:
            year = f"20{year}"
        if rest.lower() in {"fall", "autumn"} or rest == "秋":
            return f"{year} Fall"
        if rest.lower() == "spring" or rest == "春":
            return f"{year} Spring"
        if rest.lower() == "summer" or rest == "夏":
            return f"{year} Summer"
        if rest in season:
            return f"{year} {season[rest]}"
        return f"{year} {rest.title()}"
    return None


def _norm_en(name: str) -> str:
    return re.sub(r"\s+", " ", name).strip().lower()


def _self_names(text: str) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()

    def add(name: str) -> None:
        name = re.sub(r"\s+", " ", name).strip()
        if not name or name in SELF_SKIP or name in seen:
            return
        if NAME_NOISE_RE.search(name):
            return
        seen.add(name)
        names.append(name)

    for match in SELF_EN_RE.finditer(text):
        add(match.group(1))
    for match in SELF_CN_RE.finditer(text):
        add(match.group(1))
    for match in I_AM_RE.finditer(text):
        add(match.group(1))
    return names


def _names(text: str) -> list[str]:
    self_names = _self_names(text)
    if self_names:
        return self_names

    names: list[str] = []
    seen: set[str] = set()
    paired_en: set[str] = set()

    def add(name: str) -> None:
        name = re.sub(r"\s+", " ", name).strip()
        if not name or name in seen:
            return
        if not is_weak_pi_name(name) and not is_main_table_name(name):
            return
        seen.add(name)
        names.append(name)

    for match in CN_EN_PAIR_RE.finditer(text):
        add(match.group(1).lstrip("与和及、， "))
        paired_en.add(_norm_en(match.group(2)))

    for match in CN_NAMED_RE.finditer(text):
        person = match.group(1).lstrip("与和及、， ")
        if not person:
            continue
        raw = match.group(0)
        add(raw if is_weak_pi_name(f"{person}老师") or len(person) == 1 else person)

    for match in EN_TITLED_RE.finditer(text):
        english = match.group(1)
        if _norm_en(english) in paired_en:
            continue
        prefix = text[max(0, match.start() - 24) : match.start()]
        if ADVISOR_BEFORE_RE.search(prefix):
            continue
        add(english)
    return names


def _confidence(
    name: str,
    school: str | None,
    email: str | None,
    homepage: str | None,
    term: str | None,
) -> str:
    if is_weak_pi_name(name):
        return "low"
    if school and (email or homepage) and term:
        return "high"
    if school:
        return "medium"
    return "low"


def extract_opportunities(
    text: str,
    *,
    schools_path: Path | None = None,
) -> list[ExtractedOpportunity]:
    names = _names(text) or ["未知"]
    school = find_hiring_school(text, schools_path=schools_path)
    emails = _emails(text)
    email = emails[0] if emails else None
    homepage = _homepage(text)
    types = _types(text)
    areas = _areas(text)
    term = _start_term(text)
    excerpt = re.sub(r"\s+", " ", text).strip()[:160]

    rows: list[ExtractedOpportunity] = []
    for name in names:
        rows.append(
            ExtractedOpportunity(
                pi_name=name,
                school_claimed=school,
                opportunity_types=types,
                start_term=term,
                email=email,
                homepage_url=homepage,
                research_areas=areas,
                extract_confidence=_confidence(name, school, email, homepage, term),
                excerpt=excerpt,
            )
        )
    return rows
