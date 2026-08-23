#!/usr/bin/env python3
"""Build Kami-styled catalog + one page per PI."""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from html import escape
from pathlib import Path

from _paths import LISTINGS_PATH, PIS_DIR, SITE_DIST, ensure_dirs

DISCLAIMER = "信息来自小红书帖子，未经学校或导师官方核实。请以原帖和导师主页为准。"
LEDE = (
    "汇总小红书上的 CS 老师招募帖，涵盖 PhD、RA、实习与博后。"
    "本站用来发现老师；是否仍在招、如何联系，请回原帖核对。"
)
REPO_URL = "https://github.com/null1024-ws/CS-PhD-Hiring"
SITE_TITLE = "CS PhD Hiring"
STAR_SVG = (
    '<svg viewBox="0 0 16 16" aria-hidden="true">'
    '<path d="M8 .25l1.86 3.77 4.16.6-3.01 2.93.71 4.14L8 9.74l-3.72 1.95.71-4.14L1.98 4.62l4.16-.6z"/>'
    "</svg>"
)
BUSUANZI_SCRIPT = (
    '<script async src="https://busuanzi.ibruce.info/busuanzi/2.3/busuanzi.pure.mini.js"></script>'
)

TYPE_LABEL = {
    "phd": "PhD",
    "ra": "RA",
    "intern": "实习",
    "postdoc": "博后",
    "mres": "科研硕",
    "visiting": "访问",
    "other": "其他",
}

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
URL_RE = re.compile(r"https?://\S+", re.I)


def _load_listings(path: Path) -> dict:
    if not path.is_file():
        return {"generated_at": "", "listings": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _load_pis(pis_dir: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    if not pis_dir.is_dir():
        return out
    for path in pis_dir.glob("*.json"):
        out[path.stem] = json.loads(path.read_text(encoding="utf-8"))
    return out


def _uniq(items: list[str]) -> list[str]:
    seen: list[str] = []
    for item in items:
        text = (item or "").strip()
        if text and text not in seen:
            seen.append(text)
    return seen


def clean_excerpt(text: str) -> str:
    """One readable sentence: drop title noise, emails, and raw URLs."""
    text = (text or "").strip()
    text = re.sub(r"^(招生|intern|ra|phd)\s+", "", text, flags=re.I)
    text = EMAIL_RE.sub("", text)
    text = URL_RE.sub("", text)
    text = re.sub(r"(邮箱|主页)\s*", "", text)
    return re.sub(r"\s+", " ", text).strip(" 。.;；,，")


def _best_excerpt(excerpts: list[str]) -> str:
    if not excerpts:
        return ""

    def score(text: str) -> int:
        points = len(text)
        if "方向" in text or "研究" in text:
            points += 40
        if re.search(r"还招|\bintern\b", text, re.I):
            points -= 15
        return points

    return max(excerpts, key=score)


def compose_pi_view(pi: dict) -> dict:
    """Collapse many near-duplicate posts into one reading view."""
    opps = pi.get("opportunities") or []
    types = _uniq([t for opp in opps for t in (opp.get("types") or [])])
    terms = _uniq([opp.get("start_term") or "" for opp in opps])
    contacts = _uniq([opp.get("contact") or "" for opp in opps])
    sources = _uniq([opp.get("source_url") or "" for opp in opps])
    excerpts = [clean_excerpt(opp.get("excerpt") or "") for opp in opps]
    excerpts = [e for e in excerpts if e]
    excerpt = _best_excerpt(excerpts)
    if pi.get("homepage_url") and pi["homepage_url"] not in contacts:
        contacts.append(pi["homepage_url"])
    return {
        "name": pi.get("name") or "",
        "school": pi.get("school_canonical") or pi.get("school_claimed") or "",
        "country": pi.get("school_country") or "",
        "areas": _uniq(pi.get("research_areas") or []),
        "types": types,
        "terms": terms,
        "contacts": contacts,
        "excerpt": excerpt,
        "sources": sources,
        "updated": pi.get("updated_at") or "",
    }


CSS = """
@font-face {
  font-family: "TsangerJinKai02";
  src: url("https://cdn.jsdelivr.net/gh/AlfredoSequeworthy/TsangerJinKai02@main/TsangerJinKai02-W04.woff2") format("woff2");
  font-weight: 400;
  font-style: normal;
  font-display: swap;
}
@font-face {
  font-family: "TsangerJinKai02";
  src: url("https://cdn.jsdelivr.net/gh/AlfredoSequeworthy/TsangerJinKai02@main/TsangerJinKai02-W05.woff2") format("woff2");
  font-weight: 500;
  font-style: normal;
  font-display: swap;
}
:root {
  --parchment: #f5f4ed;
  --ivory: #faf9f5;
  --warm-sand: #e8e6dc;
  --brand: #1B365D;
  --brand-light: #2D5A8A;
  --brand-tint: #EEF2F7;
  --near-black: #141413;
  --dark-warm: #3d3d3a;
  --olive: #504e49;
  --stone: #6b6a64;
  --border: #e8e6dc;
  --border-soft: #e5e3d8;
  --serif: "TsangerJinKai02", "Source Han Serif SC", "Noto Serif CJK SC", "Songti SC", Georgia, serif;
  --latin-ui: "PingFang SC", system-ui, -apple-system, sans-serif;
  --measure: 760px;
}
* { box-sizing: border-box; }
html, body { margin: 0; }
body {
  background: var(--parchment);
  color: var(--near-black);
  font-family: var(--serif);
  font-size: 17px;
  font-weight: 400;
  line-height: 1.55;
  letter-spacing: 0.35px;
  -webkit-font-smoothing: antialiased;
}
a { color: var(--brand); text-decoration: none; }
a:hover { color: var(--brand-light); }
a:focus-visible, .filter-chip:focus-visible { outline: 2px solid var(--brand); outline-offset: 2px; }
.page { max-width: 1140px; margin: 0 auto; padding: 72px 40px 104px; }
.narrow { max-width: var(--measure); }
.site-top {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}
.site-top .eyebrow { margin: 0; }
.site-nav {
  font-family: var(--latin-ui);
  font-size: 13px;
  color: var(--stone);
  display: flex;
  gap: 14px;
  align-items: center;
}
.site-nav a { color: var(--stone); }
.site-nav a:hover { color: var(--brand); }
.github-star {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 12px;
  border: 1px solid var(--border);
  background: var(--ivory);
  color: var(--brand);
  font-family: var(--latin-ui);
  font-size: 12px;
  font-weight: 500;
  border-radius: 999px;
  white-space: nowrap;
  line-height: 1;
}
.github-star:hover { border-color: var(--brand); background: var(--brand-tint); color: var(--brand); }
.github-star svg { width: 14px; height: 14px; fill: currentColor; }
.eyebrow {
  font-family: var(--latin-ui);
  font-size: 12px;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: var(--stone);
  margin: 0 0 10px;
}
h1 {
  font-size: 32px;
  font-weight: 500;
  line-height: 1.2;
  color: var(--near-black);
  margin: 0 0 10px;
}
.hero { margin-bottom: 28px; }
.hero h1 {
  font-size: 46px;
  line-height: 1.1;
  letter-spacing: -0.3px;
  margin: 0 0 18px;
}
.lede { color: var(--olive); margin: 0 0 8px; max-width: var(--measure); }
.hero .lede { font-size: 19px; margin: 0; }
.disclaimer {
  background: var(--brand-tint);
  border-left: 3px solid var(--brand);
  padding: 16px 20px;
  margin: 24px 0 0;
  font-size: 15px;
  color: var(--olive);
  line-height: 1.55;
}
.toolbar { margin: 0 0 8px; }
.search {
  appearance: none;
  -webkit-appearance: none;
  width: min(320px, 100%);
  border: 0;
  border-bottom: 1px solid var(--border);
  border-radius: 0;
  background: transparent;
  color: var(--olive);
  padding: 4px 0 8px;
  margin: 0 0 18px;
  font-family: var(--latin-ui);
  font-size: 14px;
  outline: none;
}
.search:focus { border-bottom-color: var(--brand); color: var(--near-black); }
.search::placeholder { color: var(--stone); }
.filter-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 10px;
  margin: 0 0 12px;
}
.filter-k {
  font-family: var(--latin-ui);
  font-size: 13px;
  color: var(--stone);
  width: 2.5em;
  flex-shrink: 0;
}
.filter-chip {
  font-family: var(--latin-ui);
  font-size: 13px;
  padding: 8px 16px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: var(--ivory);
  cursor: pointer;
  color: var(--olive);
}
.filter-chip:hover { border-color: var(--brand-light); color: var(--brand); }
.filter-chip.active { background: var(--brand); color: var(--ivory); border-color: var(--brand); }
table { width: 100%; border-collapse: collapse; margin: 18px 0 40px; }
th {
  font-family: var(--latin-ui);
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.7px;
  text-transform: uppercase;
  color: var(--stone);
  text-align: left;
  padding: 10px 8px;
  border-bottom: 1px solid var(--border);
}
td {
  padding: 12px 8px;
  border-bottom: 1px solid var(--border-soft);
  vertical-align: top;
}
td a { font-weight: 500; }
.chip {
  display: inline-block;
  font-family: var(--latin-ui);
  font-size: 12px;
  line-height: 1.4;
  padding: 3px 10px;
  margin: 0 4px 4px 0;
  border-radius: 999px;
  background: #E4ECF5;
  color: var(--brand);
}
.back-link {
  font-family: var(--latin-ui);
  font-size: 14px;
  color: var(--stone);
  display: inline-block;
  margin: 28px 0 18px;
}
.meta-grid {
  display: grid;
  grid-template-columns: 88px 1fr;
  gap: 8px 16px;
  margin: 22px 0;
  padding: 16px 18px;
  background: var(--ivory);
  border: 1px solid var(--border-soft);
}
.meta-grid .k {
  font-family: var(--latin-ui);
  font-size: 11px;
  letter-spacing: 0.7px;
  text-transform: uppercase;
  color: var(--stone);
  padding-top: 4px;
}
.excerpt {
  margin: 8px 0 24px;
  color: var(--dark-warm);
}
.source-list { list-style: none; padding: 0; margin: 0 0 48px; }
.source-list li { margin: 0 0 8px; }
.source-list a { font-family: var(--latin-ui); font-size: 14px; }
footer.site {
  margin-top: 72px;
  padding-top: 28px;
  border-top: 1px solid var(--border-soft);
  color: var(--stone);
  font-size: 14px;
}
footer.site .visit-count { margin: 0 0 10px; font-size: 13px; }
.hidden { display: none; }
@media (max-width: 880px) {
  .page { padding: 48px 22px 72px; }
  .hero h1 { font-size: 34px; }
  .hero .lede { font-size: 17px; }
}
@media (max-width: 720px) {
  h1 { font-size: 26px; }
  .hero h1 { font-size: 28px; }
  .hero .lede { font-size: 16px; }
  .filter-chip { font-size: 12px; padding: 7px 12px; }
  table, thead, tbody, th, td, tr { display: block; width: 100%; }
  th { display: none; }
  td { border: 0; padding: 4px 0; }
  td::before {
    content: attr(data-label);
    display: block;
    font-family: var(--latin-ui);
    font-size: 11px;
    letter-spacing: 0.6px;
    text-transform: uppercase;
    color: var(--stone);
    margin-bottom: 2px;
  }
  tr { padding: 14px 0; border-bottom: 1px solid var(--border-soft); }
  .meta-grid { grid-template-columns: 1fr; }
}
"""

JS = """
const cutoffDays = 18 * 30;
function parseDate(value) {
  const t = Date.parse(value);
  return Number.isNaN(t) ? 0 : t;
}
function activeValue(group) {
  const el = document.querySelector(`.filter-chip.active[data-group="${group}"]`);
  return el ? el.dataset.value : "";
}
function applyFilters() {
  const q = document.getElementById("q").value.trim().toLowerCase();
  const country = activeValue("country");
  const area = activeValue("area");
  const typ = activeValue("type");
  const showAll = document.querySelector('.filter-chip.active[data-group="alltime"]');
  const now = Date.now();
  document.querySelectorAll("tbody tr").forEach((row) => {
    const hay = row.dataset.hay || "";
    const old = !showAll && (now - parseDate(row.dataset.updated)) > cutoffDays * 86400000;
    const ok =
      !old &&
      (!q || hay.includes(q)) &&
      (!country || row.dataset.country === country) &&
      (!area || (row.dataset.areas || "").split("|").includes(area)) &&
      (!typ || (row.dataset.types || "").split("|").includes(typ));
    row.classList.toggle("hidden", !ok);
  });
}
document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("q").addEventListener("input", applyFilters);
  document.querySelectorAll(".filter-chip").forEach((btn) => {
    btn.addEventListener("click", () => {
      const group = btn.dataset.group;
      if (group === "alltime") {
        btn.classList.toggle("active");
      } else {
        document.querySelectorAll(`.filter-chip[data-group="${group}"]`).forEach((other) => {
          other.classList.toggle("active", other === btn);
        });
      }
      applyFilters();
    });
  });
  applyFilters();
});
"""


def _type_chips(types: list[str]) -> str:
    return "".join(
        f'<span class="chip">{escape(TYPE_LABEL.get(t, t))}</span>' for t in types
    )


def _site_top() -> str:
    return (
        '<div class="site-top">'
        '<p class="eyebrow">CS-PhD-Hiring · 招募索引</p>'
        '<nav class="site-nav">'
        f'<a class="github-star" href="{REPO_URL}">{STAR_SVG}Star</a>'
        "</nav>"
        "</div>"
    )


def _site_footer(note: str) -> str:
    return (
        '<footer class="site">'
        '<p class="visit-count">Total visits: <span id="busuanzi_value_site_pv">Loading…</span></p>'
        f"<p>{note}</p>"
        "</footer>"
        f"{BUSUANZI_SCRIPT}"
    )


def _filter_row(label: str, group: str, values: list[str], labels: dict[str, str] | None = None) -> str:
    chips = [
        f'<button type="button" class="filter-chip active" data-group="{group}" data-value="">全部</button>'
    ]
    for value in values:
        text = (labels or {}).get(value, value)
        chips.append(
            f'<button type="button" class="filter-chip" data-group="{group}" '
            f'data-value="{escape(value)}">{escape(text)}</button>'
        )
    return (
        f'<div class="filter-row"><span class="filter-k">{escape(label)}</span>'
        f"{''.join(chips)}</div>"
    )


def render_index(payload: dict) -> str:
    listings = payload.get("listings") or []
    countries = sorted({row.get("school_country") for row in listings if row.get("school_country")})
    areas = sorted({a for row in listings for a in (row.get("research_areas") or [])})
    types = sorted({t for row in listings for t in (row.get("opportunity_types") or [])})
    rows = []
    for row in listings:
        name = escape(row.get("name") or "")
        path = escape(row.get("detail_path") or "")
        hay = " ".join(
            [
                row.get("name") or "",
                row.get("school_canonical") or "",
                " ".join(row.get("research_areas") or []),
            ]
        ).lower()
        rows.append(
            "<tr "
            f'data-country="{escape(row.get("school_country") or "")}" '
            f'data-areas="{"|".join(row.get("research_areas") or [])}" '
            f'data-types="{"|".join(row.get("opportunity_types") or [])}" '
            f'data-updated="{escape(row.get("updated_at") or "")}" '
            f'data-hay="{escape(hay)}">'
            f'<td data-label="更新">{escape(row.get("updated_at") or "")}</td>'
            f'<td data-label="导师"><a href="{path}">{name}</a></td>'
            f'<td data-label="学校">{escape(row.get("school_canonical") or "")}</td>'
            f'<td data-label="地区">{escape(row.get("school_country") or "")}</td>'
            f'<td data-label="方向">{escape(" · ".join(row.get("research_areas") or []))}</td>'
            f'<td data-label="机会">{_type_chips(row.get("opportunity_types") or [])}</td>'
            f'<td data-label="学期">{escape(row.get("start_term") or "")}</td>'
            "</tr>"
        )

    today = date.today().isoformat()
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{SITE_TITLE}</title>
  <style>{CSS}</style>
</head>
<body>
  <div class="page">
    {_site_top()}
    <header class="hero">
      <h1>{SITE_TITLE}</h1>
      <p class="lede">{escape(LEDE)}</p>
      <p class="disclaimer">{escape(DISCLAIMER)} 最后更新：{today}</p>
    </header>
    <div class="toolbar">
      <input id="q" class="search" type="search" placeholder="搜索老师 / 学校 / 方向" autocomplete="off">
      {_filter_row("地区", "country", countries)}
      {_filter_row("方向", "area", areas)}
      {_filter_row("机会", "type", types, TYPE_LABEL)}
      <div class="filter-row">
        <span class="filter-k">时间</span>
        <button type="button" class="filter-chip" data-group="alltime" data-value="1">含 18 个月以前</button>
      </div>
    </div>
    <main>
      <table>
        <thead>
          <tr>
            <th>更新</th><th>导师</th><th>学校</th><th>地区</th>
            <th>方向</th><th>机会</th><th>学期</th>
          </tr>
        </thead>
        <tbody>
          {''.join(rows)}
        </tbody>
      </table>
    </main>
    {_site_footer(f"CS-PhD-Hiring · {today}")}
  </div>
  <script>{JS}</script>
</body>
</html>
"""


def render_detail(pi: dict) -> str:
    view = compose_pi_view(pi)
    chips = _type_chips(view["types"])
    contacts = " · ".join(
        f'<a href="mailto:{escape(c)}">{escape(c)}</a>'
        if "@" in c and "://" not in c
        else f'<a href="{escape(c)}">{escape(c)}</a>'
        for c in view["contacts"]
    ) or "—"
    sources = "".join(
        f'<li><a href="{escape(url)}">{escape(url)}</a></li>' for url in view["sources"]
    ) or "<li>暂无原帖链接</li>"
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(view["name"])} · CS-PhD-Hiring</title>
  <style>{CSS}</style>
</head>
<body>
  <div class="page narrow">
    {_site_top()}
    <a class="back-link" href="../index.html">← 返回老师列表</a>
    <p class="eyebrow">{escape(view["country"] or "CS")}</p>
    <h1>{escape(view["name"])}</h1>
    <p class="lede">{escape(view["school"])}</p>
    <div class="meta-grid">
      <div class="k">方向</div><div>{" · ".join(escape(a) for a in view["areas"]) or "—"}</div>
      <div class="k">机会</div><div>{chips or "—"}</div>
      <div class="k">学期</div><div>{escape(" · ".join(view["terms"]) or "—")}</div>
      <div class="k">联系</div><div>{contacts}</div>
    </div>
    <p class="excerpt">{escape(view["excerpt"])}</p>
    <p class="eyebrow">原帖</p>
    <ul class="source-list">{sources}</ul>
    {_site_footer(escape(DISCLAIMER))}
  </div>
</body>
</html>
"""


def build(listings_path: Path, pis_dir: Path, out_dir: Path) -> None:
    ensure_dirs()
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "pis").mkdir(exist_ok=True)
    payload = _load_listings(listings_path)
    (out_dir / "index.html").write_text(render_index(payload), encoding="utf-8")
    for pi_id, pi in _load_pis(pis_dir).items():
        (out_dir / "pis" / f"{pi_id}.html").write_text(render_detail(pi), encoding="utf-8")
    print(f"Built site into {out_dir} ({date.today().isoformat()})")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--listings", type=Path, default=LISTINGS_PATH)
    parser.add_argument("--pis-dir", type=Path, default=PIS_DIR)
    parser.add_argument("--out", type=Path, default=SITE_DIST)
    args = parser.parse_args(argv)
    build(args.listings, args.pis_dir, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
