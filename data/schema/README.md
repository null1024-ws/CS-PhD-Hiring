# 发布数据字段

站点只读这些文件：`data/listings.json`、`data/pis/<pi_id>.json`、`data/schools.json`。原始小红书 / 一亩三分地笔记不在这里。

## `data/schools.json`

每所学校一条。`aliases` 里的任何写法都必须落到同一 `id`、`name_zh`、`country`。

规范化函数（Step 3）应对 alias 做大小写与空白折叠后再查表。

## `data/listings.json`

首页表格的一行 = 一位老师的当前视图，不是一条帖子。

| 字段 | 含义 |
| --- | --- |
| `pi_id` | 稳定 id，对应 `data/pis/<pi_id>.json` |
| `name` / `name_en` | 展示名 |
| `school_canonical` / `school_country` | 规范学校与国家/地区 |
| `school_status` | `verified` / `unverified` / `conflict` |
| `research_areas` | 方向并集 |
| `opportunity_types` | 机会类型并集 |
| `start_term` | 最近一条机会的学期，可空 |
| `source_count` | 来源帖数量 |
| `updated_at` | 最近更新，ISO 日期 |
| `detail_path` | 详情页相对路径 |

## `data/pis/<pi_id>.json`

详情页：老师字段 + `opportunities[]` + `school_evidence[]`。机会对象见 `opportunity.schema.json`。

## 枚举

- `school_status`: `verified` | `unverified` | `conflict`
- `opportunity.types`: `phd` | `ra` | `intern` | `postdoc` | `mres` | `visiting` | `other`
- `contact_class`: `academic` | `consumer_email` | `social_only` | `none`
- `source`: `xhs` | `github` | `1p3a`
- `source_kind`: `pi` | `repost` | `agency` | `unknown`
- `relevance`: `cs` | `review` | `notcs`
- `extract_confidence`: `high` | `medium` | `low`
