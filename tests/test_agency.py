from agency import classify_contact, classify_source_kind, should_list_source
from extract import extract_opportunities
from school_normalize import normalize_school

from conftest import FIXTURES

AGENCY = FIXTURES / "agency"


def test_witty_agency_without_academic_contact() -> None:
    body = (AGENCY / "witty_agency.txt").read_text(encoding="utf-8")
    comments = "老师邮箱是 fake.wash@ust.hk 欢迎联系"
    visible = body
    assert classify_contact(visible) == "social_only"
    assert classify_contact(visible + "\n" + comments) == "academic"
    kind = classify_source_kind(
        visible_text=visible,
        pi_name="未知",
        school_claimed=None,
        school_resolvable=False,
    )
    assert kind == "agency"
    assert not should_list_source(kind, classify_contact(visible))


def test_real_pi_with_email_kept() -> None:
    text = (AGENCY / "pi_with_email.txt").read_text(encoding="utf-8")
    row = extract_opportunities(text)[0]
    kind = classify_source_kind(
        visible_text=text,
        pi_name=row.pi_name,
        school_claimed=row.school_claimed,
        school_resolvable=normalize_school(row.school_claimed) is not None,
    )
    assert classify_contact(text) == "academic"
    assert kind == "pi"
    assert should_list_source(kind, "academic")


def test_ocr_email_counts_as_academic() -> None:
    body = (AGENCY / "ocr_email.txt").read_text(encoding="utf-8")
    ocr = (AGENCY / "ocr_email.ocr.txt").read_text(encoding="utf-8")
    visible = f"{body}\n{ocr}"
    assert classify_contact(body) == "none"
    assert classify_contact(visible) == "academic"
    kind = classify_source_kind(
        visible_text=visible,
        pi_name="陈思远",
        school_claimed="港科大",
        school_resolvable=True,
    )
    assert kind == "pi"
    assert should_list_source(kind, "academic")


def test_student_repost_kept() -> None:
    text = (AGENCY / "student_repost.txt").read_text(encoding="utf-8")
    row = extract_opportunities(text)[0]
    kind = classify_source_kind(
        visible_text=text,
        pi_name=row.pi_name,
        school_claimed=row.school_claimed,
        school_resolvable=normalize_school(row.school_claimed) is not None,
    )
    assert classify_contact(text) == "none"
    assert kind == "repost"
    assert should_list_source(kind, "none")
