from onepoint_parse import parse_forum_list, parse_thread, thread_to_note

from conftest import FIXTURES

ONEPOINT = FIXTURES / "onepoint"


def test_forum_list_keeps_threads_skips_board_links() -> None:
    html = (ONEPOINT / "forum_list.html").read_text(encoding="utf-8")
    rows = parse_forum_list(html)
    tids = {row["tid"] for row in rows}
    titles = {row["title"] for row in rows}
    assert tids == {"4821001", "4821002"}
    assert any("Ada Ng" in title for title in titles)
    assert any("intern" in title.lower() for title in titles)
    assert all("1point3acres.com" in row["url"] for row in rows)
    assert all("forumdisplay" not in row["url"] for row in rows)
    assert {row["posted_at"] for row in rows} == {"2026-08-20", "2026-08-18"}


def test_thread_uses_op_body_not_reply() -> None:
    html = (ONEPOINT / "thread.html").read_text(encoding="utf-8")
    url = "https://www.1point3acres.com/bbs/thread-4821001-1-1.html"
    thread = parse_thread(html, url=url)
    note = thread_to_note(thread)
    assert thread["tid"] == "4821001"
    assert "Ada Ng" in thread["title"]
    assert "ada.ng@nus.edu.sg" in thread["desc"]
    assert "楼主邮箱在楼上" not in thread["desc"]
    assert note["source"] == "1p3a"
    assert note["note_id"] == "1p3a-4821001"
    assert note["source_url"] == url
