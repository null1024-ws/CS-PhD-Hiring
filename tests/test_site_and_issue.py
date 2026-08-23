from __future__ import annotations

from build_site import DISCLAIMER, build, clean_excerpt, compose_pi_view
from import_issue import parse_issue
from run_pipeline import load_notes, merge_records, process_note, write_outputs

from conftest import FIXTURES


def _built_site(tmp_path):
    notes = load_notes(FIXTURES / "notes")
    records = [r for note in notes for r in process_note(note) if r["listable"]]
    listings = tmp_path / "listings.json"
    pis = tmp_path / "pis"
    write_outputs(merge_records(records), listings, pis)
    out = tmp_path / "dist"
    build(listings, pis, out)
    return out


def test_homepage_has_no_verification_ui(tmp_path) -> None:
    html = (_built_site(tmp_path) / "index.html").read_text(encoding="utf-8")
    assert "陈思远" in html
    assert "李明" in html
    assert "校验" not in html
    assert "已核对" not in html
    assert "冲突" not in html
    assert DISCLAIMER in html
    assert "本站用来发现老师" in html
    assert "CS PhD Hiring" in html
    assert "非官方招募索引" not in html
    assert "busuanzi_site_pv" in html
    assert "cdn.busuanzi.cc" in html
    assert "学期" not in html
    assert "<select" not in html
    assert "filter-chip" in html
    assert "#f5f4ed" in html
    assert "TsangerJinKai02" in html
    assert "王强" not in html


def test_detail_is_one_reading_not_two_posts(tmp_path) -> None:
    out = _built_site(tmp_path)
    chen = next(p for p in (out / "pis").glob("*.html") if "陈思远" in p.read_text(encoding="utf-8"))
    text = chen.read_text(encoding="utf-8")
    assert "https://www.xiaohongshu.com/explore/n1" in text
    assert "https://www.xiaohongshu.com/explore/n2" in text
    assert "chen.siyuan@ust.hk" in text
    assert text.count("招收 PhD") <= 1
    assert "类型：phd" not in text
    assert "类型：intern" not in text
    assert "学校核对" not in text
    assert "校验" not in text
    assert DISCLAIMER in text
    assert "busuanzi_site_pv" in text
    assert "cdn.busuanzi.cc" in text
    assert "学期" not in text
    assert "邮箱" in text
    assert "主页" in text
    assert "max-width: 720px" in text


def test_compose_merges_duplicate_excerpts() -> None:
    view = compose_pi_view(
        {
            "name": "陈思远",
            "school_canonical": "香港科技大学",
            "school_country": "中国香港",
            "research_areas": ["systems"],
            "homepage_url": "https://www.cs.ust.hk/~siyuan",
            "opportunities": [
                {
                    "types": ["phd"],
                    "start_term": "2026 Fall",
                    "contact": "chen.siyuan@ust.hk",
                    "excerpt": "招生 陈思远教授（港科大）2026 Fall 招收 PhD。邮箱 chen.siyuan@ust.hk",
                    "source_url": "https://xhs.example/n1",
                },
                {
                    "types": ["intern"],
                    "start_term": "2026 Summer",
                    "contact": "chen.siyuan@ust.hk",
                    "excerpt": "intern 陈思远教授 港科大 还招 intern，邮箱 chen.siyuan@ust.hk",
                    "source_url": "https://xhs.example/n2",
                },
            ],
        }
    )
    assert view["types"] == ["phd", "intern"]
    assert view["emails"] == ["chen.siyuan@ust.hk"]
    assert view["homepages"] == ["https://www.cs.ust.hk/~siyuan"]
    assert len(view["sources"]) == 2
    assert view["excerpt"].count("邮箱") == 0
    assert "http" not in view["excerpt"]
    assert clean_excerpt("招生 陈思远教授 邮箱 a@b.edu") == "陈思远教授"


def test_issue_import_is_not_auto_verified() -> None:
    body = (FIXTURES / "issue_sample.md").read_text(encoding="utf-8")
    note = parse_issue(body)
    assert note["source"] == "github"
    rows = [r for r in __import__("run_pipeline", fromlist=["process_note"]).process_note(note)]
    assert all(r["source"]["source"] == "github" for r in rows)
    assert all(r["school_status"] != "verified" for r in rows)
