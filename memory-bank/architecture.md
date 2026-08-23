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
| `scripts/extract.py` | 纯文本抽取 |
| `scripts/relevance.py` | `cs` / `review` / `notcs` |
| `scripts/agency.py` | 联系方式分级与中介判定（只看正文+OCR） |
| `scripts/verify_school.py` | 主页/OpenAlex 文本核对学校 |
| `scripts/dedup.py` | 同名同校合并 |
| `scripts/ocr_extract.py` | 图片 OCR |
| `scripts/content_bundle.py` | 正文 + OCR + 有用评论 |
| `scripts/xhs_collect.py` | 小红书采集（需本机登录） |
| `scripts/search_queries.py` | 招生搜索词 |
| `scripts/run_pipeline.py` | 串联到 listings / pis |
| `scripts/import_issue.py` | GitHub Issue → note |
| `scripts/build_site.py` | Kami / CityU 式首页（hero + chip 筛选，无原生 select）+ 一位老师一页（去重摘录，无校验 UI） |
| `site/dist/` | 构建产物，gitignore |
| `.github/workflows/pages.yml` | 用仓库里的 `listings.json` + `pis/` 建站后发布 Pages |
| `.github/ISSUE_TEMPLATE/add-hiring.yml` | 访客补条 |

## Pipeline

`note` → `bundle_visible_text`（标题+正文+OCR）→ 抽取 / 相关性 / 中介 → `verify_school` → `merge_records` → `listings.json` + `pis/*.json` → `site/dist`.

主表只收：`relevance=cs` 且 `source_kind` 为 `pi`/`repost` 且姓名不是「张老师」这类弱名。中介与 `notcs` 不出现。

## School quality

自称学校不能直接相信。`verified` 必须有主页或索引文本与别名表一致。URL 里的 `mit.edu` 不得当成学校别名 `MIT`。

## Not in git

- Cookie / `~/.xhs-cli/`
- `data/raw/` 除 `.gitignore` 外
- `site/dist/`
