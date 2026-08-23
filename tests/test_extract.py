from __future__ import annotations

from extract import extract_opportunities, is_main_table_name, research_topics

from conftest import FIXTURES

EXTRACT = FIXTURES / "extract"


def _load(name: str) -> str:
    return (EXTRACT / name).read_text(encoding="utf-8")


def test_complete_post_is_high_confidence() -> None:
    rows = extract_opportunities(_load("complete_phd.txt"))
    assert len(rows) == 1
    row = rows[0]
    assert row.pi_name == "陈思远"
    assert row.school_claimed == "港科大"
    assert "phd" in row.opportunity_types
    assert row.start_term == "2026 Fall"
    assert row.email == "chen.siyuan@ust.hk"
    assert row.homepage_url == "https://www.cs.ust.hk/~siyuan"
    assert row.research_areas
    assert row.extract_confidence == "high"
    assert is_main_table_name(row.pi_name)


def test_title_fragments_are_not_listable() -> None:
    assert not is_main_table_name("讲席")
    assert not is_main_table_name("担任助理")
    assert not is_main_table_name("有幸听过")
    assert not is_main_table_name("在麻")
    assert not is_main_table_name("从孙燕妮")
    assert not is_main_table_name("美籍华人")
    assert not is_main_table_name("香港")
    assert not is_main_table_name("创智学院")
    assert not is_main_table_name("发邮件给")
    assert not is_main_table_name("极主动和")
    assert not is_main_table_name("关于")
    assert not is_main_table_name("这个")
    assert is_main_table_name("陈思远")
    assert is_main_table_name("周尚辰")
    assert is_main_table_name("张伟楠")
    assert is_main_table_name("Ming Li")


def test_laoshi_prefix_is_not_a_pi_name() -> None:
    rows = extract_opportunities(
        "大家好，我是这个实验室的学生。请发邮件给导师。"
        "信跟着陈老师申请。也祝陈老师。和俞勇教授、兄周尚辰教授、为张伟楠教授招 PhD，港科大。"
    )
    names = {row.pi_name for row in rows}
    assert "周尚辰" in names
    assert "张伟楠" in names
    assert "俞勇" in names
    assert names.isdisjoint(
        {
            "这个",
            "发邮件给",
            "信跟着陈",
            "兄周尚辰",
            "为张伟楠",
            "香港",
            "祝陈",
            "和俞勇",
        }
    )


def test_zhang_laoshi_is_low_and_not_listable() -> None:
    rows = extract_opportunities(_load("zhang_laoshi.txt"))
    assert len(rows) == 1
    row = rows[0]
    assert row.pi_name == "张老师"
    assert row.extract_confidence == "low"
    assert not is_main_table_name(row.pi_name)


def test_two_professors_split() -> None:
    rows = extract_opportunities(_load("two_pis.txt"))
    names = {row.pi_name for row in rows}
    assert names == {"王伟", "李娜"}
    assert all(row.school_claimed == "NUS" for row in rows)
    assert all("phd" in row.opportunity_types for row in rows)


def test_intern_type_extracted() -> None:
    rows = extract_opportunities(_load("intern.txt"))
    assert len(rows) == 1
    row = rows[0]
    assert row.pi_name == "Ming Li"
    assert "intern" in row.opportunity_types
    assert row.school_claimed == "MIT"
    assert row.start_term == "2026 Summer"


def test_two_digit_fall_term() -> None:
    rows = extract_opportunities("陈思远教授 港科大 26 fall 招 PhD")
    assert rows[0].start_term == "2026 Fall"


def test_self_intro_is_hiring_pi_not_advisors() -> None:
    rows = extract_opportunities(_load("self_intro_advisors.txt"))
    assert [row.pi_name for row in rows] == ["Yuejiang Liu"]
    assert rows[0].school_claimed in {"新加坡国立大学", "NUS"}
    assert "Yilun Du" not in {row.pi_name for row in rows}
    assert "Chelsea Finn" not in {row.pi_name for row in rows}
    assert "Stanford" not in (rows[0].school_claimed or "")
    assert "斯坦福" not in (rows[0].school_claimed or "")


def test_wojiao_english_name_not_nationality() -> None:
    rows = extract_opportunities(
        "招 CS / HCI 博士生。Hi! 我叫 Anna Fang，目前就读于卡内基梅隆大学。"
        "我是美籍华人教授的学生。"
    )
    assert [row.pi_name for row in rows] == ["Anna Fang"]


def test_joining_nyuad_from_self_intro() -> None:
    rows = extract_opportunities(
        "NYUAD 新ap招Phd。大家好，我是 Jiahao Yu，之后会加入 NYU Abu Dhabi担任TTAP。"
    )
    assert [row.pi_name for row in rows] == ["Jiahao Yu"]
    assert rows[0].school_claimed in {"NYUAD", "NYU Abu Dhabi"}


def test_cn_en_pair_is_one_person() -> None:
    ntu = extract_opportunities(_load("cn_en_pair.txt"))
    assert {row.pi_name for row in ntu} == {"丛林"}
    hku = extract_opportunities(
        "香港大学iLab诚邀英才加入，讲席教授吕伟生（Prof. Wilson Lu）"
        "和陈俊杰教授（Prof. Junjie Chen）领衔。"
    )
    assert {row.pi_name for row in hku} == {"吕伟生", "陈俊杰"}


def test_research_topics_are_short_bullets() -> None:
    text = (
        "NYUAD 新ap招Phd和Postdoc 大家好，我是 Jiahao Yu。"
        "过去做过 LLM security、fuzzing、program repair。"
        "1. Software / System Security\n2. LLM / RL / Trustworthy AI\n"
        "欢迎感兴趣的同学邮件联系：jy5951@nyu.edu"
    )
    topics = research_topics(text)
    assert "fuzzing" in topics
    assert "program repair" in topics
    assert "Software / System Security" in topics
    assert all(len(topic) < 50 for topic in topics)
    assert all("欢迎来港科大" not in topic for topic in topics)


def test_self_intro_not_collaborators_or_url_school() -> None:
    text = (
        "本人招生：招收博士生。大家好！我是顾尚定（Shangding Gu，"
        "主页：https://people.eecs.berkeley.edu/~shangding.gu/index.html）。"
        "之后在 UC Berkeley EECS 从事博士后研究，主要与 Prof. Dawn Song "
        "和 Prof. Costas Spanos 合作。我将于 2026 年秋季学期加入上海交通大学计算机学院，"
        "担任 Tenure-Track Associate Professor。"
    )
    rows = extract_opportunities(text)
    names = {row.pi_name for row in rows}
    assert names == {"顾尚定"}
    assert rows[0].school_claimed in {"上海交通大学", "上海交大", "SJTU"}
    assert "Dawn Song" not in names
    assert "Costas Spanos" not in names
    assert "Berkeley" not in (rows[0].school_claimed or "")


def test_advisor_names_are_not_hiring_pis() -> None:
    text = (
        "【帮导师招生】创智学院MLSys AP招RA/PhD。"
        "冯思远老师现任上海创智学院助理教授。"
        "冯老师在上海交通大学获得计算机科学博士学位，导师为张伟楠教授和俞勇教授。"
    )
    rows = extract_opportunities(text)
    names = {row.pi_name for row in rows}
    assert "冯思远" in names
    assert "张伟楠" not in names
    assert "俞勇" not in names
    assert rows[0].school_claimed in {"上海创智学院", "创智学院"}


def test_joining_school_beats_current_student_school() -> None:
    rows = extract_opportunities(
        "招 CS / HCI 博士生。我叫 Anna Fang，目前就读于卡内基梅隆大学。"
        "我将于 2026 年加入墨尔本大学，担任助理教授。"
    )
    assert [row.pi_name for row in rows] == ["Anna Fang"]
    assert rows[0].school_claimed in {"墨尔本大学", "University of Melbourne"}


def test_joining_mbzuai_not_stanford_postdoc() -> None:
    rows = extract_opportunities(
        "[本人招生] ATLAS Lab @ MBZUAI。大家好，我是吴冬夏。"
        "我即将加入 MBZUAI 担任 Tenure-track Assistant Professor。"
        "我目前在斯坦福大学从事博士后研究。"
    )
    assert [row.pi_name for row in rows] == ["吴冬夏"]
    assert rows[0].school_claimed == "MBZUAI"


def test_homepage_does_not_swallow_following_chinese() -> None:
    rows = extract_opportunities(
        "大家好，我是沈俞，目前在香港理工大学担任助理教授。"
        "我的个人主页是：https://shenyu-official.icu。今年准备招收几名 PhD学生。"
    )
    assert rows[0].homepage_url == "https://shenyu-official.icu"
    assert "今年准备" not in (rows[0].homepage_url or "")


def test_does_not_invent_email_or_term() -> None:
    rows = extract_opportunities(_load("no_contact.txt"))
    assert len(rows) == 1
    row = rows[0]
    assert row.pi_name == "陈思远"
    assert row.school_claimed == "港科大"
    assert row.email is None
    assert row.start_term is None
    assert "ust.hk" not in (row.excerpt or "")
    assert row.extract_confidence != "high"
