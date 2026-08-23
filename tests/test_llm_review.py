from __future__ import annotations

from llm_review import parse_review_json, review_research


WU_TEXT = (
    "大家好，我是吴冬夏(Dongxia Wu)。我即将加入 MBZUAI 担任 Tenure-track Assistant Professor。"
    "主要研究方向包括：\n* 可信大模型/生成模型\n* 多模态模型\n* 科学智能体\n* 概率机器学习\n"
    "* AI for Science / Biology\n如何申请\n请附上：\n1. CV\n2. 成绩单\n3. 代表性论文及简短研究兴趣介绍"
)


def test_parse_review_json_keeps_only_known_areas() -> None:
    parsed = parse_review_json(
        '{"research_areas": ["ml", "biology", "nlp"], "research_topics": ["可信大模型/生成模型", "成绩单"]}'
    )
    assert parsed is not None
    assert parsed["research_areas"] == ["ml", "nlp"]
    assert "可信大模型/生成模型" in parsed["research_topics"]


def test_review_uses_llm_not_application_materials() -> None:
    def fake(_user: str) -> str:
        return (
            '{"research_areas": ["ml", "nlp"], '
            '"research_topics": ["可信大模型/生成模型", "多模态模型", "科学智能体", "概率机器学习", "AI for Science"]}'
        )

    reviewed = review_research(WU_TEXT, name="吴冬夏", school="MBZUAI", completer=fake)
    assert reviewed is not None
    assert "computer vision" not in reviewed["research_areas"]
    assert "security" not in reviewed["research_areas"]
    assert "ml" in reviewed["research_areas"]
    assert "成绩单" not in reviewed["research_topics"]
    assert "CV" not in reviewed["research_topics"]
    assert "可信大模型/生成模型" in reviewed["research_topics"]


def test_review_cache_skips_completer() -> None:
    called = {"n": 0}

    def fake(_user: str) -> str:
        called["n"] += 1
        return '{"research_areas": ["systems"], "research_topics": ["should not run"]}'

    cache = {
        "n1": {
            "research_areas": ["ml"],
            "research_topics": ["概率机器学习"],
        }
    }
    reviewed = review_research(
        WU_TEXT,
        note_id="n1",
        cache=cache,
        completer=fake,
    )
    assert called["n"] == 0
    assert reviewed == {"research_areas": ["ml"], "research_topics": ["概率机器学习"]}


def test_invalid_llm_json_returns_none() -> None:
    assert review_research(WU_TEXT, completer=lambda _: "not json") is None
