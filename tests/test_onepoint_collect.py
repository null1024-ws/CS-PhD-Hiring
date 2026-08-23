from __future__ import annotations

import json
from pathlib import Path

import onepoint_collect
from onepoint_collect import main as collect_main

from conftest import FIXTURES

ONEPOINT = FIXTURES / "onepoint"


def test_from_dir_writes_note_without_network(tmp_path: Path, monkeypatch) -> None:
    def boom(url: str, timeout: float = 20.0) -> dict:
        raise AssertionError(f"network should not run: {url}")

    monkeypatch.setattr(onepoint_collect, "fetch_page", boom)
    out = tmp_path / "out"
    code = collect_main(
        ["--from-dir", str(ONEPOINT), "--out-dir", str(out), "--sleep", "0", "--max-threads", "3"]
    )
    assert code == 0
    notes = [p for p in out.glob("1p3a-*.json")]
    assert notes
    note = json.loads(notes[0].read_text(encoding="utf-8"))
    assert note["source"] == "1p3a"
    assert note["note_id"].startswith("1p3a-")
    assert "1point3acres.com" in note["source_url"]
    assert note["desc"]
    index = json.loads((out / "index.json").read_text(encoding="utf-8"))
    assert note["note_id"].removeprefix("1p3a-") in index["tids"]


def test_live_block_does_not_corrupt_index(tmp_path: Path, monkeypatch) -> None:
    out = tmp_path / "out"
    out.mkdir()
    index_path = out / "index.json"
    original = {"tids": {"1": {"note_id": "1p3a-1", "url": "kept"}}, "pages": []}
    index_path.write_text(json.dumps(original), encoding="utf-8")

    monkeypatch.setattr(
        onepoint_collect,
        "fetch_page",
        lambda url, timeout=20.0: {
            "error": "cloudflare",
            "message": "cloudflare on " + url,
            "url": url,
        },
    )
    code = collect_main(["--out-dir", str(out), "--sleep", "0"])
    err_index = json.loads(index_path.read_text(encoding="utf-8"))
    assert code == 3
    assert err_index == original
    assert not list(out.glob("1p3a-*.json"))


def test_live_not_configured_leaves_missing_index(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        onepoint_collect,
        "fetch_page",
        lambda url, timeout=20.0: {"error": "not_configured", "message": "no browser", "url": url},
    )
    out = tmp_path / "empty"
    code = collect_main(["--out-dir", str(out), "--sleep", "0"])
    assert code == 2
    assert not (out / "index.json").exists()
