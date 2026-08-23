# Implementation Plan — CS-PhD-Hiring

每一步都小、可独立验收、不含代码。未经验证不要开始下一步。

## Step 1 — 仓库骨架与忽略规则

建立目录约定：`data/`、`data/raw/`、`data/pis/`、`scripts/`、`site/`、`tests/fixtures/`。写 `.gitignore`，确保 Cookie、原图、原始笔记不会被提交。写最短 README：项目一句话、数据来自小红书、非官方。

**验证**：`git status` 看不到 `data/raw` 样例文件；README 在 GitHub 预览里能读懂项目是什么。

## Step 2 — 发布数据 schema 与学校别名表

写清 `listings.json` / `pi` / `opportunity` 的字段说明（可用 JSON Schema 或带注释的样例）。放入一份真实感的学校别名表（至少覆盖港校、常见美英新缩写、内地 C9 常见写法）。

**验证**：用一份「港科大 / HKUST / 香港科技大学」样例，人工确认会落到同一规范名和「中国香港」。

## Step 3 — 学校名规范化函数

实现：输入任意学校字符串，输出规范名 + 国家，或「无法识别」。覆盖大小写、中英、常见缩写。

**验证**：pytest 至少包含：HKUST、港科大、MIT、清华、NUS、未知乱码。缩写与全称必须相同；乱码不得误判成某所大学。

## Step 4 — 抽取规则（纯文本 fixture）

准备 3–5 条脱敏招生文本（含 PhD、intern、只写张老师、一帖两老师）。实现从纯文本抽出：姓名、自称学校、机会类型、学期、邮箱、主页、方向。

**验证**：pytest 断言：完整帖抽出高置信字段；「张老师」为 low 且可被主表策略丢掉；两老师拆成两条；邮箱与学期不被编造。

## Step 5 — CS 相关性判断

实现：根据方向文本打 `cs` / `review` / `notcs`。准备正例（LLM 安全、机器人、HCI）和反例（纯湿实验、公司金融）。

**验证**：pytest 正例进 `cs`，反例进 `notcs`；模棱两可不得标 `cs`。

## Step 5b — 科研中介过滤

实现：只根据标题+正文+OCR 判断联系方式级别（`academic` / `consumer_email` / `social_only` / `none`），评论区一律忽略。再按设计文档打 `source_kind`。准备四类脱敏文本：1）诙谐正常、无邮箱/主页、引导私信；2）真老师正文含学校邮箱或主页；3）正文空白、OCR 图里有学校邮箱；4）学生转发，有具体老师+学校、无联系方式、无私信引导。

**验证**：pytest：1 必须 `agency` 且不得进主表；2 与 3 必须保留；4 为 `repost` 可保留。不得因为文风正常就把 1 放行。评论区里的邮箱不得把 1 洗白。

## Step 6 — 学校校验（主页文本 + 冲突）

实现校验器：输入老师名、自称学校、可选主页文本、可选 OpenAlex 单位列表，输出 `verified` / `unverified` / `conflict` 和证据。不在这一步打真实网络。

**验证**：三条 fixture——主页含同一学校 → verified；无证据 → unverified；主页/索引是另一所学校 → conflict。conflict 不得变成 verified。

## Step 7 — 去重合并

实现：同一规范名 + 规范学校合并；学校都未知且无主页则不合并。合并后机会类型取并集，来源列表保留。

**验证**：pytest：同一老师两帖一行、两条来源；同名不同校两行；两名「未知学校」的张三不合并。

## Step 8 — 图片 OCR 接入（离线 fixture）

实现：给定已下载的测试图片，OCR 成文本并写入 bundle。沿用 EasyOCR 中英。准备一张含「招生 / 学校名」的小图 fixture（自制，非小红书原图）。

**验证**：对该图跑 OCR，输出文件里能找到预期关键词；无图笔记不会失败。

## Step 9 — Bundle 合并

实现：把笔记正文、有用评论、OCR 文本合成抽取输入。无登录、只读 fixture。

**验证**：只有图的笔记，抽取输入必须含 OCR；纯问答评论不覆盖正文里的学校。

## Step 10 — 采集脚本（本机，可先空跑）

移植 CityU-CS-Guide 的 search / read / checkpoint / 限速，但 query 改为招生关键词。未登录必须明确退出。

**验证**：未登录时命令失败信息含 `xhs login`，且不写坏 index。维护者登录后（你来跑）至少能抓到 1 条真实笔记并出现在 `data/raw/`。

## Step 11 — 流水线串联到 `listings.json`

一条命令：bundle → 抽取 → 相关性 → 校验 → 去重 → 写出 `data/listings.json` 与 `data/pis/`。校验若需网络，允许跳过 OpenAlex、只靠主页文本与别名。

**验证**：对 fixture 跑通后，listings 行数、conflict 标记、来源链接与预期一致。

## Step 12 — 首页可筛表格

构建脚本生成 `site/dist/index.html`，读 listings，列字段按设计文档。筛选：国家、方向、机会类型、校验状态、关键词。默认隐藏 18 个月以前和 `pi_name` 低置信。

**验证**：本地打开首页，fixture 中的老师可见；点筛选只剩目标国家；conflict 行有可见标记。

## Step 13 — 老师详情纸感页

为每个 pi 生成详情页：学校与证据、机会列表、摘录、原帖链接。视觉跟随 Kami / CityU-CS-Guide。首页老师名链到详情。

**验证**：从首页点进详情，证据和两条来源都在；原帖链接可点；移动宽度下文字不溢出。

## Step 14 — GitHub Issue 补条

加 Issue 模板。导入脚本把填写后的 markdown/front matter 变成 opportunity，再进同一流水线。

**验证**：用一份样例 Issue 正文导入，listings 出现 `source=github`；其学校仍经过校验，不因 Issue 自称而直接 verified。

## Step 15 — 发布与免责声明

GitHub Actions：对 `site/dist` 发 Pages。首页/详情有免责声明。README 写清：如何采集、如何本地建站、如何用 fixture 测。

**验证**：Actions 配置能通过语法检查；本地 `build_site` 产物含声明；README 按文档走一遍 fixture 建站成功。

## Step 16 — 一亩三分地招生帖离线解析

准备脱敏的招生版帖表 HTML 和一篇楼主帖 HTML（自制，非整页镜像）。实现：从帖表抽出 tid / 标题 / 原帖 URL / 日期；从帖文抽出标题和正文；转成与现有流水线相同的 `note`（`source=1p3a`）。无网络。

**验证**：pytest 能解析出至少一条招生帖的 tid、标题、正文片段和 `1point3acres.com` 原帖链接；置顶广告或非 thread 链接不会变成帖子。

## Step 17 — 一亩三分地本机采集（可先空跑）

保守拉 fid=173 第一页新帖并读楼主正文。限速、checkpoint、Cloudflare/验证码停跑。原始 HTML 只写 `data/raw/1p3a/`。

**验证**：对本地 fixture HTML 跑采集入口不访问网络也能写出 note；未配置浏览器时命令失败信息不写坏 index。

## Step 18 — 一亩三分地进入同一流水线

`run_pipeline` 能读 `source=1p3a` 的 note，与小红书记录一起抽取、过滤、去重。详情原帖标签能看出是一亩三分地。

**验证**：fixture 流水线里出现 `source=1p3a` 的可列表老师；中介帖仍不进主表。

## Step 19 — 研究方向由 LLM 审阅

规则抽取继续负责姓名、学校、邮箱、机会类型。`research_areas` / `research_topics` 交给 LLM：只保留帖子里写明的科研方向，申请材料（CV、成绩单、论文列表）不得进方向。无密钥时读已审缓存；测试注入假模型。

**验证**：吴冬夏类 fixture 经审阅后方向为可信大模型/多模态/科学智能体等，不得出现成绩单或把申请 CV 当成 computer vision。无网络、无密钥时 pytest 仍绿。
