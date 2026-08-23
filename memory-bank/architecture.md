# Architecture

## Layout

| 路径 | 职责 |
| --- | --- |
| `README.md` | 项目说明、fixture 建站、采集、补条 |
| `AGENTS.md` | 写代码前先读 memory-bank |
| `data/schools.json` | 学校别名表 |
| `data/listings.json` | 主表发布数据（当前来自 fixture 流水线） |
| `data/pis/` | 老师详情 JSON |
| `data/schema/` | 字段说明与 JSON Schema |
| `data/raw/` | 本机原始抓取，gitignore |
| `scripts/school_normalize.py` | 学校别名规范化 |
| `scripts/extract.py` | 纯文本抽取。自报「我是」优先；不把合作者/导师/URL 里的学校当成招生方。学校取即将加入/现任，不取伯克利主页或师从单位 |
| `scripts/relevance.py` | `cs` / `review` / `notcs` |
| `scripts/agency.py` | 联系方式分级与中介判定（只看正文+OCR） |
| `scripts/verify_school.py` | 主页/OpenAlex 文本核对学校 |
| `scripts/dedup.py` | 同名同校合并 |
| `scripts/ocr_extract.py` | 图片 OCR |
| `scripts/content_bundle.py` | 正文 + OCR + 有用评论 |
| `scripts/xhs_collect.py` | 小红书采集（需本机登录） |
| `scripts/onepoint_parse.py` | 一亩三分地招生版 HTML → note（离线解析） |
| `scripts/onepoint_collect.py` | fid=173 采集：`--from-dir` 离线；线上先 httpx，被拦再可选 Crawl4AI（`--browser` / `--headed`）。Cloudflare 停跑。原始 HTML/note 写 `data/raw/1p3a/` |
| `scripts/search_queries.py` | 招生搜索词 |
| `scripts/run_pipeline.py` | 串联到 listings / pis，并写 `data/audit.json`。可重复 `--input-dir`（小红书 + `1p3a`） |
| `scripts/audit_pipeline.py` | 流水线审计：收录 / 丢弃原因 / 警告 |
| `scripts/import_issue.py` | GitHub Issue → note |
| `scripts/build_site.py` | Kami / CityU 式首页 + 详情。访问量只显示本页 pv（不蒜子 `site_pv` 会和同域名其他站混计） |
| `index.html` / `pis/` / `.nojekyll` | GitHub Pages 当前按 **main 仓库根** 发布；没有 `index.html` 时会回退成 README |
| `site/dist/` | 本机构建产物，gitignore |
| `.github/workflows/pages.yml` | 用仓库里的 `listings.json` + `pis/` 建到 `site/dist`；只有 Pages 源改成 GitHub Actions 后才会用到 |
| `.github/ISSUE_TEMPLATE/add-hiring.yml` | 访客补条 |

## Pipeline

`note`（`xhs` / `1p3a` / `github`）→ `bundle_visible_text`（标题+正文+OCR）→ 抽取 / 相关性 / 中介 → `verify_school` → `merge_records` → `listings.json` + `pis/*.json` → `site/dist`（本地）以及仓库根 `index.html` / `pis/`（Pages）。

主表只收：`relevance=cs` 且 `source_kind` 为 `pi`/`repost` 且姓名能通过姓氏/英文全名校验。中介、`notcs`、句子切片弱名不出现。`audit.json` 含 `weak_name` 与 `by_reason`。

## School quality

自称学校不能直接相信。`verified` 必须有主页或索引文本与别名表一致。URL 里的 `mit.edu` 不得当成学校别名 `MIT`。

## Not in git

- Cookie / `~/.xhs-cli/` / 一亩三分地 Cookie
- `data/raw/` 除 `.gitignore` 外（含 `data/raw/1p3a/`）
- `site/dist/`
