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
SKIP_URL_HOST = re.compile(
    r"xiaohongshu\.com|xhslink\.com|weixin\.qq\.com|1point3acres\.com", re.I
)

CN_TITLE_RE = re.compile(r"(助理教授|副教授|教授|老师)")
EN_TITLED_RE = re.compile(
    r"(?:Prof\.?|Dr\.?|Professor)\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){1,2})"
)
SELF_EN_RE = re.compile(
    r"(?:我是|我叫)\s*([A-Z][A-Za-z]+(?:[\s\-]+[A-Z][A-Za-z]+){1,3})"
)
SELF_CN_RE = re.compile(
    r"(?:我是|我叫)\s*([\u4e00-\u9fff]{2,4})(?=[，。！!,\s（(]|目前|即将|老师|教授|$)"
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
ADVISOR_BEFORE_RE = re.compile(
    r"(师从|指导下|毕业于|此前|曾在|合作|导师为|导师是|主要与|和\s+Prof)"
)
HIRE_SCHOOL_RE = re.compile(
    r"(?:即将加入|将加入|会加入|现已加入|入职|现任|将于[^。\n]{0,24}加入)\s*([^。\n]{2,80})"
)
PAST_AFFILIATION_RE = re.compile(
    r"(?:目前在|目前就读|师从|毕业于|获得[^。]{0,20}学位|此前|曾在|导师为|导师是)[^。\n]*"
)
URL_STRIP_RE = re.compile(r"https?://[^\s)）,\"']+", re.I)
SELF_SKIP = {"学生", "楼主", "本人", "老师", "作者", "招生"}
WEAK_NAME_RE = re.compile(r"^(?:未知|老师|教授|[\u4e00-\u9fff]老师)$")
NAME_NOISE_RE = re.compile(
    r"教授|老师|助理|讲席|担任|研究所|听过|科学系|特聘|校长|教研|接发|荐麻|等教授|美轨|美籍|华裔|课题|实验室|"
    r"学院|大学|讲座|教轨|准聘|长聘|教职|轨道|邮件|关注|跟着|主动|恭喜|创智"
)
NAME_STOPWORDS = {
    "这个",
    "以及",
    "关于",
    "并且",
    "还有",
    "或者",
    "香港",
    "台湾",
    "北京",
    "上海",
    "同学",
    "学生",
    "导师",
    "课题组",
}
# Common surnames so "发邮件给陈老师" cannot become 发邮件给.
CN_SURNAMES = frozenset(
    "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜"
    "戚谢邹喻柏水窦章云苏潘葛奚范彭郎鲁韦昌马苗凤花方俞任袁柳鲍史唐"
    "费廉岑薛雷贺倪汤滕殷罗毕郝邬安常乐于时傅皮卞齐康伍余元卜顾孟平"
    "黄和穆萧尹姚邵湛汪祁毛禹狄米贝明臧计伏成戴谈宋茅庞熊纪舒屈项祝"
    "董梁杜阮蓝闵季麻强贾路娄危江童颜郭梅盛林刁钟徐邱骆高夏蔡田樊胡"
    "凌霍虞万柯卢莫房裘缪解应宗丁宣贲邓郁单杭洪包诸左石崔吉钮龚程嵇"
    "邢滑裴陆荣翁荀羊惠甄曲家封芮羿储靳邴松井富巫乌焦巴弓牧隗山谷车"
    "侯宓蓬全郗班仰秋仲伊宫宁仇栾暴甘钭厉戎祖武符刘景詹束龙叶幸司韶"
    "郜黎蓟薄印宿白怀蒲邰从鄂索咸籍赖卓蔺屠蒙池乔阴胥能苍双闻德崔"
    "肖丛贾潘"
)
COMPOUND_SURNAMES = frozenset(
    {"欧阳", "司马", "上官", "诸葛", "司徒", "夏侯", "皇甫", "公孙", "慕容", "宇文", "东方", "令狐", "端木", "南宫", "闻人"}
)
NAME_CONJ = set("和与及为给跟也请向")
NAME_VERB2 = set("祝跟给为")
NAME_PARTICLE = set("也再还并请就")

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
    research_topics: list[str] = field(default_factory=list)
    extras: dict = field(default_factory=dict)


def is_weak_pi_name(name: str) -> bool:
    return not name or bool(WEAK_NAME_RE.fullmatch(name.strip()))


def is_main_table_name(name: str) -> bool:
    """Main table hides 张老师 / 未知 and sentence slices before 老师/教授."""
    name = (name or "").strip()
    if is_weak_pi_name(name) or name in NAME_STOPWORDS or NAME_NOISE_RE.search(name):
        return False
    if name.endswith(("的", "和", "给", "任")):
        return False
    if re.match(r"^(从|在|于|地|有|据|任|接)", name):
        return False
    if re.fullmatch(r"[\u4e00-\u9fff]+", name):
        if len(name) in {2, 3}:
            return name[0] in CN_SURNAMES
        if len(name) == 4:
            return name[:2] in COMPOUND_SURNAMES
        return False
    return bool(re.fullmatch(r"[A-Za-z][A-Za-z.\-]+(?:\s+[A-Z][A-Za-z.\-]+)+", name))


def _cn_titled_names(text: str) -> list[str]:
    """Take the 2–3 characters immediately before 老师/教授 if they look like a name."""
    names: list[str] = []
    for match in CN_TITLE_RE.finditer(text):
        prefix = text[max(0, match.start() - 24) : match.start()]
        if ADVISOR_BEFORE_RE.search(prefix):
            continue
        window_chars: list[str] = []
        for char in reversed(text[max(0, match.start() - 4) : match.start()]):
            if "\u4e00" <= char <= "\u9fff":
                window_chars.append(char)
            else:
                break
        window = "".join(reversed(window_chars))
        found = ""
        for length in (3, 2):
            if len(window) < length:
                continue
            candidate = window[-length:]
            if length == 3 and candidate[0] in NAME_CONJ:
                tail = candidate[1:]
                if is_main_table_name(tail) and not (
                    tail[0] in NAME_VERB2 and tail[1] in CN_SURNAMES
                ):
                    found = tail
                    break
                continue
            if length == 2:
                before = window[-3] if len(window) >= 3 else ""
                if before in NAME_PARTICLE:
                    continue
                if candidate[0] in NAME_VERB2 and candidate[1] in CN_SURNAMES:
                    continue
            if is_main_table_name(candidate):
                found = candidate
                break
        if found:
            names.append(found)
        elif window:
            if match.group(1) == "教授" and prefix.endswith(
                ("讲席", "特聘", "客座", "兼职", "访问", "讲座")
            ):
                continue
            weak = f"{window[-1]}老师"
            if is_weak_pi_name(weak):
                names.append(weak)
    return names


@lru_cache(maxsize=1)
def _alias_list(path: str) -> list[str]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    aliases = [alias for row in payload["schools"] for alias in row["aliases"]]
    return sorted(set(aliases), key=len, reverse=True)


def _text_without_urls(text: str) -> str:
    return URL_STRIP_RE.sub(" ", text or "")


def find_claimed_school(text: str, *, schools_path: Path | None = None) -> str | None:
    """Longest alias that appears in the text. Ignore URLs; short ASCII aliases need word boundaries."""
    text = _text_without_urls(text)
    aliases = _alias_list(str(schools_path or SCHOOLS_PATH))
    for alias in aliases:
        if re.search(r"[A-Za-z]", alias) and len(alias) <= 5:
            if re.search(rf"(?<![\w.]){re.escape(alias)}(?![\w.])", text, re.I):
                return alias
        elif alias in text or alias.lower() in text.lower():
            return alias
    return None


def find_hiring_school(text: str, *, schools_path: Path | None = None) -> str | None:
    """Prefer the school the PI is joining or now at, not a collaborator or alma mater."""
    path = schools_path
    text = _text_without_urls(text)
    for match in HIRE_SCHOOL_RE.finditer(text):
        school = find_claimed_school(match.group(1), schools_path=path)
        if school:
            return school
    head = text.split("\n", 1)[0]
    school = find_claimed_school(head, schools_path=path)
    if school:
        return school
    stripped = PAST_AFFILIATION_RE.sub(" ", text)
    return find_claimed_school(stripped, schools_path=path)


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


TOPIC_SKIP_RE = re.compile(
    r"入学|背景|奖学金|GPA|宝子|勾搭|Nice|快乐|氛围|Case|全奖|津贴|海鲜|避坑|套磁|海投|"
    r"博士后|访问学|招收|本科|硕士|优先|好奇|热情|工程能力|沟通|专业素养|成长|"
    r"联系|规划|申请|欢迎|实习生"
)
TOPIC_LEAD_RE = re.compile(
    r"(?:过去做过|研究方向(?:包括)?|目前主要研究方向包括|重点关注|"
    r"如果你对)([^。\n]{4,160}?)(?:等[。.]|感兴趣|。|$)"
)
TOPIC_ITEM_RE = re.compile(
    r"(?:^|[\n;；。]|[•·])\s*(?:\d+[.、]|[•·\-])\s*([^\n。]{2,80})"
)


def _ok_topic(text: str) -> bool:
    topic = re.sub(r"\s+", " ", text or "").strip(" .。；;，,：:")
    if not topic or len(topic) < 2 or len(topic) > 48:
        return False
    if TOPIC_SKIP_RE.search(topic):
        return False
    if topic.lower() in {"phd", "intern", "ra", "postdoc", "cs"}:
        return False
    return True


def research_topics(text: str) -> list[str]:
    """A few concrete directions, not a marketing paragraph."""
    found: list[str] = []
    seen: set[str] = set()

    def add(raw: str) -> None:
        topic = re.split(r"[：:（(]", raw, 1)[0].strip()
        topic = re.sub(r"\s+", " ", topic).strip(" .。；;，,")
        key = topic.lower()
        if not _ok_topic(topic) or key in seen:
            return
        seen.add(key)
        found.append(topic)

    for match in TOPIC_ITEM_RE.finditer(text or ""):
        add(match.group(1))
    for match in TOPIC_LEAD_RE.finditer(text or ""):
        for part in re.split(r"[、，,/]| and ", match.group(1)):
            add(part.strip(" 的在为"))
    return found[:8]


def research_excerpt(text: str) -> str:
    topics = research_topics(text)
    if topics:
        return " · ".join(topics)
    return " · ".join(_areas(text))


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
        person = match.group(1)
        if is_main_table_name(person):
            add(person)
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

    for person in _cn_titled_names(text):
        add(person)

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
    topics = research_topics(text)
    excerpt = " · ".join(topics) if topics else " · ".join(areas)

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
                research_topics=topics,
                extract_confidence=_confidence(name, school, email, homepage, term),
                excerpt=excerpt,
            )
        )
    return rows
