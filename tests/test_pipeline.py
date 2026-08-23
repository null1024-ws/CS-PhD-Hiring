from __future__ import annotations

import json
from pathlib import Path

from run_pipeline import load_notes, merge_records, process_note, write_outputs
from xhs_collect import main as collect_main

from conftest import FIXTURES


def test_collect_unauthenticated_mentions_login(capsys, monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XHS_BIN", str(tmp_path / "no-such-xhs"))
    code = collect_main(["--max-notes", "1", "--sleep", "0"])
    err = capsys.readouterr().err
    assert code == 2
    assert "xhs login" in err
    assert not (tmp_path / "index.json").exists()


def test_pipeline_fixture_listings(tmp_path: Path) -> None:
    notes = load_notes(FIXTURES / "notes")
    records: list[dict] = []
    for note in notes:
        records.extend(process_note(note))
    listable = [r for r in records if r["listable"]]
    merged = merge_records(listable)
    payload = write_outputs(merged, tmp_path / "listings.json", tmp_path / "pis")
    names = {row["name"] for row in payload["listings"]}
    assert "陈思远" in names
    chen = next(row for row in payload["listings"] if row["name"] == "陈思远")
    assert chen["source_count"] == 2
    assert chen["school_status"] == "verified"
    assert "李明" in names
    li = next(row for row in payload["listings"] if row["name"] == "李明")
    assert li["school_status"] == "conflict"
    assert li["school_status"] != "verified"
    assert li.get("suggested_school") == "麻省理工学院"
    assert all("私信" not in json.dumps(row, ensure_ascii=False) for row in payload["listings"])
    assert "王强" not in names
    detail = json.loads((tmp_path / "pis" / f"{chen['pi_id']}.json").read_text(encoding="utf-8"))
    assert len(detail["opportunities"]) == 2
    assert {o["source_url"] for o in detail["opportunities"]} == {
        "https://www.xiaohongshu.com/explore/n1",
        "https://www.xiaohongshu.com/explore/n2",
    }
