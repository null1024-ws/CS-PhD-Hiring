# Design Document — CS-PhD-Hiring

## 1. Goal

做一个可筛选的公开站点：从小红书收集 CS 相关老师的招生/招募帖（不限于 PhD），整理成「老师存在 + 当前机会」索引。列表交互参考 [DuoOffer](https://duooffer.github.io/)，采集与纸感详情参考 [CityU-CS-Guide](https://github.com/null1024-ws/CityU-CS-Guide)。

核心差异：

- 数据源是小红书，不是一亩三分地。
- 学校字段必须经过自动核对，不能把帖子里的单位原文直接当任职学校。
- 一条帖子的价值首先是「发现这位老师」，机会类型是附加属性。

## 2. Scope

### In scope (v1)

- 用 `xhs-cli` 按关键词搜索并抓取笔记正文、评论、图片。
- 对图片做 OCR，正文 + OCR 合并后再抽取。
- 抽出老师、学校、国家/地区、方向、机会类型、学期、联系方式、原帖。
- 用主页或公开学术资料核对学校，给出 `verified` / `unverified` / `conflict`。
- 去重合并同一老师的多条帖子。
- 丢掉科研中介帖、明显非招募、明显非 CS 的帖。中介帖常写得正常甚至诙谐，不以语气或广告词为主要依据。
- 静态站：表格筛选 + 老师详情页。
- GitHub Issue 模板补一条漏网信息，经脚本导入同一数据文件。

### Non-goals (v1)

- 不抓一亩三分地、不镜像 DuoOffer 数据。
- 不做账号系统、推荐匹配、邮件订阅、聊天机器人。
- 不在站点上展示小红书原图或完整笔记备份。
- 不保证录取结果、不评价老师好坏。
- 不自动群发咨询邮件。
- 不把 Cookie / 登录态写入仓库。

## 3. User journeys

### 3.1 申请者浏览

1. 打开首页表格，默认按更新时间倒序。
2. 用国家/地区、学校、方向、机会类型、学校校验状态筛选；用关键词搜老师名或方向。
3. 点老师名进入详情：任职学校与校验证据、方向、最近机会列表、原文摘录、小红书原帖链接。
4. 点原帖离开本站，自行核对。

### 3.2 维护者更新

1. 本机已 `xhs login`。
2. 跑采集（支持断点、限速）。
3. 跑图片下载 + OCR + 抽取 + 校验 + 去重。
4. 看校验报告：`conflict` 和空学校优先人工改数据文件。
5. 重建静态站并发布。

### 3.3 访客补一条

1. 用 GitHub Issue 模板填老师、学校、方向、机会类型、原帖链接。
2. 维护者合并或跑导入脚本；该条 `source=github`，学校仍走同一套校验。

## 4. Feature behavior

### 4.1 采集

复用 CityU-CS-Guide 的采集纪律，不复用它的「按课号」模型。

- 工具：`xhs-cli`（Camoufox），比逆向 API 稳。
- 搜索：一组全局中文/英文关键词（如「CS PhD 招生」「计算机 博士 招生 2026」「招收 PhD intern」「组里招 RA」等），按方向再补若干条（NLP、CV、系统、安全、机器人、HCI）。
- 每条 query 只取首页结果，保守限速，checkpoint 可续跑。
- 同一 `note_id` 被多个 query 命中则记交叉引用，不重复抓取。
- 登录失败或验证码：停跑并提示，不重试打爆风控。

### 4.2 文本合并

每条笔记生成一个 bundle：

- 标题、正文
- 评论里像补充招生信息的句子（联系方式、截止日期、学校更正）
- 全部图片 OCR 文本（带平均置信度）

公开站点只用摘录，不发布 bundle 全文。

### 4.3 抽取

从 bundle 抽出一条或多条 **opportunity**，并挂到一个 **PI**。

必填（缺了也能进「待补全」但不进主表）：

- `pi_name`（允许「未知」，但主表默认隐藏）
- `school_claimed`（帖子自称的学校，可空）
- `opportunity_types`（可多选）
- `source_note_id` + `source_url`

选填：`homepage_url`、`email`、`research_areas`、`start_term`、`country`、`excerpt`、`contact_note`。

机会类型枚举：`phd` | `ra` | `intern` | `postdoc` | `mres` | `visiting` | `other`。

抽取策略（v1 不强制在线 LLM）：

- 邮箱、主页 URL、学期（2026 Fall / 26fall / 春博 / 暑研）用规则。
- 老师名、学校别名、方向标签用规则 + 学校别名表。
- 抽不到的字段留空，`extract_confidence` 为 `low`，进入待补全，不编造。

### 4.4 CS 相关性

默认收录：CS、AI/ML、NLP、CV、系统、安全、HCI、机器人、数据挖掘、编程语言、理论 CS。

可收录（自行判断）：ECE / 信息学院里明显做上述方向的老师；AI for Science 若方法主体是 ML/系统也可收。

不收录：纯湿实验生物、化学合成、土木结构、公司金融、临床医学（无计算）等。标记 `notcs` 的条目不进主表，可留在内部审计里。

不确定：`relevance=review`，默认不进主表。

### 4.5 科研中介过滤（硬需求）

科研中介帖的表面可以和真招生帖一样正常、甚至更好玩，**不能靠文风、emoji、是否「像广告」来判**。

用户给出的稳定信号：中介 **不敢在正文里介绍自己的邮箱或主页**。他们要的是私信/加微信，而不是让读者绕过他们去找老师。

只在 **标题 + 正文 + 图片 OCR** 里找联系方式。评论区不算「介绍自己」——谁都可以在评论里补一条。

联系方式分级：

| 级别 | 算什么 | 例子 |
| --- | --- | --- |
| `academic` | 学术联系，不像中介本人在揽客 | 学校邮箱、`.edu` / 大学域名邮箱、老师个人主页、实验室页 |
| `consumer_email` | 弱信号，不够洗白 | Gmail / QQ / 163，且无主页 |
| `social_only` | 典型中介转化路径 | 仅有私信、加微信、评论区扣 1、看主页小红书号 |
| `none` | 正文完全不留自己的联系方式 | — |

判定：

1. 显式中介词（代申、中介、包 offer、文书全程、选校定位收费等）→ `source_kind=agency`，丢掉。
2. 正文+OCR 没有 `academic` 联系，且存在 `social_only` 引导 → `agency`，丢掉。这是主规则：看起来再正常也丢。
3. 正文+OCR 没有 `academic` 联系，也没有可核验的具体老师名+学校 → `agency` 或 `unknown`，不进主表。
4. 没有邮箱/主页，但抽出了具体老师且学校能核对 → 视为学生转发真招生（`repost`），可进主表；联系方式空着即可。
5. 正文没有、图里 OCR 到学校邮箱或主页 → 算 `academic`，保留。真老师海报经常把邮箱写在图上。
6. 只有消费邮箱、没有主页 → `review`，默认不进主表。

禁止：因为帖子「写得很像老师」或「没有中介二字」就放行。

### 4.6 学校校验（硬需求）

DuoOffer 的典型失败：同名、转校、把合作单位/访问单位/招聘文案里的旧单位写成现职。

校验输入：`pi_name`、`school_claimed`、`homepage_url`（若有）。

步骤：

1. 用学校别名表把 `school_claimed` 规范成 `school_canonical`（中英全称 + 国家）。
2. 若有主页：抓取公开 HTML 文本，在页面里找学校名/机构名。
3. 再用公开学术索引查同名作者的近期单位（优先 OpenAlex；命中 CS 教师名单则加分）。
4. 比较 `school_canonical` 与外部证据：
   - 一致 → `school_status=verified`，写下证据链接。
   - 无外部证据 → `unverified`，主表仍显示帖子学校，但打灰标。
   - 外部单位与帖子冲突 → `conflict`，主表显示帖子学校，并用醒目标出「资料显示可能为 X」。
5. 帖子没写学校、外部也没有 → 学校显示「未知」，`unverified`。

禁止：用合作高校、会议举办地、联合培养单位覆盖现职，除非主页把该单位写成 affiliation。

### 4.7 去重

身份键：`normalized_pi_name + school_canonical`。若学校未知，则 `normalized_pi_name + homepage_host`，再不行就先不合并。

同一身份下合并多条机会与多条来源。主表一行 = 一位老师的当前视图（最近更新时间、机会类型并集、方向并集）。详情页列出每条来源。

### 4.8 站点

- 首页：Kami 纸感目录表。列：更新、导师、学校、地区、方向、机会、学期。不展示校验状态。
- 筛选：地区、方向、机会类型、关键词。
- 详情：一位老师一页。机会类型与学期合并展示，只留一条去重摘录、一组联系方式、一组原帖链接。不展示学校核对或冲突徽章。
- 页脚免责声明：社区信息，非官方，以原帖和导师主页为准。
- 视觉：Kami / CityU-CS-Guide 同套 token（`#f5f4ed` 纸、`#1B365D` 墨蓝、TsangerJinKai02）。

### 4.9 GitHub 补条

Issue 模板字段与 opportunity schema 对齐。导入脚本把合法 Issue 变成 `source=github` 记录，再跑同一校验。不信任 Issue 里的学校字段。

## 5. Edge cases

| 情况 | 处理 |
| --- | --- |
| 老师名只写「张老师」 | `pi_name` 保留原文，`extract_confidence=low`，默认不进主表 |
| 一帖多个老师 | 拆成多条 opportunity，分别校验 |
| 图文学校不一致 | 视为 `conflict` 线索，以校验结果为准 |
| OCR 很差 | `ocr_confidence` 低则降低抽取置信度；无正文且 OCR 空则 skip |
| 中介帖写得很正常/诙谐 | 不看文风。正文+OCR 无自己的邮箱/主页，且引导私信/微信 → `agency`，不进主表 |
| 中介只在评论区留联系方式 | 评论不算「介绍自己」，仍按正文判断 |
| 真老师邮箱写在海报图里 | OCR 到学校邮箱或主页 → `academic`，保留 |
| 学生转发真招生、正文无联系方式 | 能抽出具体老师且学校可核 → `repost`，可进主表 |
| 只有 Gmail/QQ、无主页 | `review`，默认不进主表 |
| 已毕业/停止招生的旧帖 | 仍归档，主表默认只显示最近 18 个月，可切换「全部」 |
| 转校 | 外部近单位与帖子不同 → `conflict`，不自动改帖子原文 |
| 同名不同人 | 不合并学校不同的记录；无学校则不合并 |
| 小红书链接失效 | 保留 note id 与摘录，链接标 stale |
| 验证码中断采集 | 保存 checkpoint，下次从断点继续 |

## 6. Data model

### 6.1 `note`（内部，默认不发布）

`note_id`, `url`, `fetched_at`, `queries[]`, `title`, `desc`, `comments[]`, `image_paths[]`, `ocr_text`, `ocr_confidence`

### 6.2 `pi`（发布）

```text
pi_id
name
name_en?
school_claimed
school_canonical
school_country
school_status          # verified | unverified | conflict
school_evidence[]      # {source, url, snippet, fetched_at}
homepage_url?
research_areas[]
updated_at
```

### 6.3 `opportunity`（发布）

```text
opportunity_id
pi_id
types[]                # phd/ra/intern/postdoc/mres/visiting/other
start_term?
excerpt
contact?
contact_class          # academic | consumer_email | social_only | none
source                 # xhs | github
source_kind            # pi | repost | agency | unknown
source_url
source_note_id?
posted_at?
collected_at
relevance              # cs | review | notcs
extract_confidence     # high | medium | low
```

### 6.4 站点输入

`data/listings.json`：主表行（pi 当前视图 + 机会摘要 + 来源计数）。  
`data/pis/<pi_id>.json`：详情页数据。  
`data/schools.json`：学校别名 → 规范名、国家。

Cookie、原始笔记、原图不进 git。测试用少量脱敏 fixture。

## 7. Acceptance criteria

1. 不登录小红书也能用仓库里的 fixture 跑通「bundle → 抽取 → 校验 → 建站」，并得到可打开的本地首页。
2. 主表每行能跳到详情，详情能跳到来源 URL。
3. 学校冲突的 fixture 必须显示 `conflict`，且不得把错误学校写成 `verified`。
4. 学校一致的 fixture 必须显示 `verified` 并带证据链接。
5. 非 CS 帖、以及「看起来正常但正文+OCR 无邮箱/主页且引导私信」的中介 fixture 不出现在主表。真老师海报把邮箱写在图里的 fixture 必须保留。
6. 同一老师两条帖子合并为一行，详情保留两条来源。
7. 只有图片、文字为空的 fixture，OCR 文本必须进入抽取输入。
8. Issue 模板字段能被导入脚本读成一条 `source=github` 记录。
9. 页面声明数据来自小红书社区，非官方。
10. 仓库内无 Cookie、无小红书原图、无完整笔记镜像。

## 8. Open defaults (locked unless you change them)

- 托管：GitHub Pages 静态站。
- 主表默认时间窗：18 个月。
- v1 抽取不依赖付费 LLM。
- 原始抓取留在本机 `data/raw/`，gitignore。
