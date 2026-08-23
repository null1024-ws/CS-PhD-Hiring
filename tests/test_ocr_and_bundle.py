from __future__ import annotations

from pathlib import Path

from content_bundle import bundle_extract_text, bundle_visible_text, flatten_collected_note
from ocr_extract import ocr_note_images


class FakeReader:
    def readtext(self, path: str):
        return [([(0, 0), (1, 0), (1, 1), (0, 1)], "港科大 招生", 0.99)]


def test_ocr_writes_keywords(tmp_path: Path) -> None:
    note_id = "poster-fixture"
    image_dir = tmp_path / note_id
    image_dir.mkdir()
    (image_dir / "0.png").write_bytes(
        b"\x89PNG\r\n\x1a\n" + b"0" * 16
    )
    out = tmp_path / "ocr"
    payload = ocr_note_images(note_id, image_dir=image_dir, out_dir=out, reader=FakeReader())
    assert "招生" in payload["full_text"]
    assert "港科大" in payload["full_text"]
    saved = (out / f"{note_id}.json").read_text(encoding="utf-8")
    assert "招生" in saved


def test_ocr_without_images_does_not_fail(tmp_path: Path) -> None:
    payload = ocr_note_images("empty-note", image_dir=tmp_path / "missing", out_dir=tmp_path)
    assert payload["full_text"] == ""
    assert payload["pages"] == []


def test_image_only_bundle_includes_ocr() -> None:
    note = {"title": "", "desc": "", "ocr_text": "港科大 招生 chen@ust.hk", "comments": []}
    text = bundle_extract_text(note)
    assert "港科大" in text
    assert "chen@ust.hk" in text


def test_question_comments_do_not_override_school() -> None:
    note = {
        "title": "招生",
        "desc": "陈思远教授 港科大 招 PhD",
        "ocr_text": "",
        "comments": ["有了解不", "同问", "其实是 MIT 吧？求问"],
    }
    visible = bundle_visible_text(note)
    assert "港科大" in visible
    assert "MIT" not in visible
    extract = bundle_extract_text(note)
    assert "港科大" in extract
    assert "MIT" not in extract


def test_flatten_keeps_fixture_and_unwraps_raw() -> None:
    fixture = {"note_id": "n1", "title": "招生", "desc": "港科大", "source": "xhs"}
    assert flatten_collected_note(fixture)["desc"] == "港科大"
    raw = {
        "note_id": "abc",
        "read": {
            "ok": True,
            "data": {
                "items": [
                    {"note_card": {"title": "招 PhD", "desc": "陈思远 港科大", "time": 1754006400}}
                ]
            },
        },
        "note": {"items": [{"note_card": {"title": "招 PhD", "desc": "陈思远 港科大", "time": 1754006400}}]},
        "comments": {"data": {"comments": [{"content": "邮箱 a@ust.hk"}]}},
        "search_item": {"id": "abc"},
    }
    note = flatten_collected_note(raw)
    assert note["title"] == "招 PhD"
    assert "港科大" in note["desc"]
    assert note["source_url"].endswith("/abc")
    assert note["comments"][0]["content"] == "邮箱 a@ust.hk"
