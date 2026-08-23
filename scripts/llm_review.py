"""LLM review of research fields. Rules do not decide what counts as a topic."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable

from _paths import LLM_REVIEWS_PATH

AREA_TAGS = (
    "nlp",
    "computer vision",
    "systems",
    "security",
    "robotics",
    "hci",
    "ml",
    "theory",
)

REVIEW_PROMPT = """你审阅的是计算机相关老师的招生帖（标题+正文）。规则抽取已经标过姓名和学校，但研究方向经常把申请材料、职位名、学校简称误当成科研方向。

只根据帖子里「这位老师自己做的研究」作答。不要编造帖子没写的方向。

## 不要当成研究方向
- 申请材料：CV / Resume / 简历、成绩单、推荐信、代表性论文清单、研究兴趣介绍（作为投递附件时）
- 职位与招募：PhD、intern、RA、postdoc、访问学生、全奖、名额
- 学校缩写或城市：MBZUAI、HKU、阿布扎比
- 合作高校、毕业学校、当前博后单位，除非正文把它写成课题方向
- 把申请用的「CV」理解成 computer vision

## research_areas
只能从这些标签里多选：nlp, computer vision, systems, security, robotics, hci, ml, theory
- 大模型 / LLM / 生成模型 / 多模态 / 科学智能体 / 概率机器学习 / AI for Science → ml；若明确做语言或 LLM 也可加 nlp
- 可信 / trustworthy / alignment，若没有攻击、隐私、系统安全、漏洞，不要标 security
- 多模态不等于 computer vision；只有写了视觉 / 图像 / 视频 / 3D 才加 computer vision
- 帖子没写方向就返回空数组，不要靠学校或职位猜

## research_topics
2–8 条短短语，尽量沿用正文「研究方向 / 关于我 / 实验室方向」里的原词，去掉编号和 emoji。
没有写明就返回空数组。

只输出一个 JSON 对象，不要 markdown：
{"research_areas": ["ml"], "research_topics": ["可信大模型/生成模型"]}
"""

Completer = Callable[[str], str]


def load_review_cache(path: Path | None = None) -> dict[str, dict]:
    target = path or LLM_REVIEWS_PATH
    if not target.is_file():
        return {}
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def save_review_cache(cache: dict[str, dict], path: Path | None = None) -> None:
    target = path or LLM_REVIEWS_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")


def build_user_message(text: str, *, name: str = "", school: str = "") -> str:
    who = f"抽取姓名：{name or '未知'}\n抽取学校：{school or '未知'}\n\n"
    return who + "帖子原文：\n" + (text or "").strip()[:6000]


def parse_review_json(raw: str) -> dict | None:
    blob = (raw or "").strip()
    if blob.startswith("```"):
        blob = blob.strip("`")
        if blob.lower().startswith("json"):
            blob = blob[4:]
        blob = blob.strip()
    try:
        data = json.loads(blob)
    except json.JSONDecodeError:
        start = blob.find("{")
        end = blob.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            data = json.loads(blob[start : end + 1])
        except json.JSONDecodeError:
            return None
    if not isinstance(data, dict):
        return None
    areas = [
        item
        for item in data.get("research_areas") or []
        if isinstance(item, str) and item in AREA_TAGS
    ]
    topics: list[str] = []
    seen: set[str] = set()
    for item in data.get("research_topics") or []:
        if not isinstance(item, str):
            continue
        topic = " ".join(item.split()).strip(" .。；;，,")
        key = topic.lower()
        if not topic or len(topic) > 48 or key in seen:
            continue
        seen.add(key)
        topics.append(topic)
    return {"research_areas": areas[:8], "research_topics": topics[:8]}


def openai_completer(prompt: str, user: str) -> str:
    key = os.environ.get("LLM_REVIEW_KEY") or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("no LLM key")
    url = os.environ.get("LLM_REVIEW_URL") or "https://api.openai.com/v1/chat/completions"
    model = os.environ.get("LLM_REVIEW_MODEL") or "gpt-4o-mini"
    body = json.dumps(
        {
            "model": model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": user},
            ],
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload["choices"][0]["message"]["content"]


def review_research(
    text: str,
    *,
    name: str = "",
    school: str = "",
    note_id: str | None = None,
    cache: dict[str, dict] | None = None,
    completer: Completer | None = None,
    prompt: str = REVIEW_PROMPT,
) -> dict | None:
    if note_id and cache is not None and note_id in cache:
        parsed = parse_review_json(json.dumps(cache[note_id], ensure_ascii=False))
        if parsed:
            return parsed
    user = build_user_message(text, name=name, school=school)
    if completer is None:
        if not (os.environ.get("LLM_REVIEW_KEY") or os.environ.get("OPENAI_API_KEY")):
            return None
        completer = lambda user_msg: openai_completer(prompt, user_msg)
    try:
        raw = completer(user)
    except (RuntimeError, KeyError, urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None
    parsed = parse_review_json(raw)
    if parsed and note_id and cache is not None:
        cache[note_id] = parsed
    return parsed
