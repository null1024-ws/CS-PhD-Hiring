from __future__ import annotations

from extract import extract_opportunities, is_main_table_name

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
    assert is_main_table_name("陈思远")
    assert is_main_table_name("Ming Li")


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
