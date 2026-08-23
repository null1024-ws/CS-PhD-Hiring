from audit_pipeline import build_audit
from build_site import render_index
from run_pipeline import process_note

from conftest import FIXTURES


def test_audit_drops_consulting_pitch() -> None:
    text = (FIXTURES / "agency" / "consulting_pitch.txt").read_text(encoding="utf-8")
    records = process_note(
        {
            "note_id": "pitch1",
            "title": "推荐麻老师组",
            "desc": text,
            "source": "xhs",
            "source_url": "https://www.xiaohongshu.com/explore/pitch1",
            "updated_at": "2026-04-18",
        }
    )
    payload = build_audit(records)
    assert payload["counts"]["agency"] >= 1
    assert all(not row["listable"] for row in records)
    assert any(row["reason"] == "agency" for row in payload["dropped"])


def test_index_lists_newest_first() -> None:
    html = render_index(
        {
            "listings": [
                {
                    "name": "Old PI",
                    "school_canonical": "港科大",
                    "school_country": "中国香港",
                    "research_areas": ["hci"],
                    "opportunity_types": ["phd"],
                    "updated_at": "2025-01-01",
                    "detail_path": "pis/old.html",
                },
                {
                    "name": "New PI",
                    "school_canonical": "NUS",
                    "school_country": "新加坡",
                    "research_areas": ["ml"],
                    "opportunity_types": ["phd"],
                    "updated_at": "2026-08-22",
                    "detail_path": "pis/new.html",
                },
            ]
        }
    )
    assert html.index("New PI") < html.index("Old PI")
