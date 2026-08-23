# Progress

## Step 1 — 仓库骨架与忽略规则（已确认）

建立目录约定与 `.gitignore`。README 写明小红书来源、非官方、原文不入库。

## Step 2 — 发布数据 schema 与学校别名表（已确认）

`data/schema/` + `data/schools.json`。港科大/HKUST/香港科技大学同校；港科广分开。

## Step 3 — 学校名规范化函数（已确认）

`normalize_school` 精确别名匹配，乱码不误判。

## Step 4 — 抽取规则（已确认）

完整帖 `high`；`张老师` 不可进主表；两教授拆条；不编造邮箱/学期。

## Step 5 — CS 相关性

正例（LLM 安全 / 机器人 / HCI）为 `cs`；湿实验与公司金融为 `notcs`；只写「人工智能」为 `review`。

## Step 5b — 科研中介过滤

诙谐无邮箱/主页 + 私信 → `agency`。评论区邮箱不能洗白。真老师邮箱或 OCR 图内邮箱保留。学生转发可核老师为 `repost`。

## Step 6 — 学校校验

主页一致 → `verified`；无证据 → `unverified`；主页/索引另一所学校 → `conflict`，不得变成 `verified`。

## Step 7 — 去重合并

同名同校合并并保留多来源；同名不同校、未知学校同名均不合并。

## Step 8 — OCR

`ocr_extract.py` 在本机调用 EasyOCR；测试用注入 reader，无图笔记不失败，输出含「招生 / 港科大」。

## Step 9 — Bundle

图文 OCR 进入抽取输入；纯问答评论不覆盖正文学校。

## Step 10 — 采集脚本

`xhs_collect.py` 未登录 / 无 CLI 时退出码 2，stderr 含 `xhs login`，不写坏 index。真实抓取需维护者本机 `xhs login`。

## Step 11 — 流水线

`run_pipeline.py` 对 `tests/fixtures/notes`：陈思远一行两来源且 verified；李明 conflict；中介与非 CS 不进表。

## Step 12 — 首页表格

可按国家/方向/类型/校验/关键词筛选；conflict 有可见标记；默认隐藏 18 个月前。

## Step 13 — 详情纸感页

暖纸墨蓝；证据与多条原帖链接；移动宽度换行。

## Step 14 — GitHub 补条

Issue 模板 + `import_issue.py`。`source=github`，自称学校不会直接 verified。

## Step 15 — 发布与免责

`.github/workflows/pages.yml` 用仓库数据建 `site/dist`。首页/详情有非官方声明。

仓库 Pages 目前是 **分支根目录**，不是 Actions。线上曾回退成 README；根目录已放入构建后的 `index.html`、`pis/` 和 `.nojekyll`。

当前 `pytest`：61+ passed。

## Step 16 — 一亩三分地招生帖离线解析（已确认）

`scripts/onepoint_parse.py` 从脱敏帖表/楼主 HTML 抽出 tid、标题、正文和原帖 URL，转成 `source=1p3a` 的 note。版规、帮助、`javascript` 链接不进帖。无网络。

## Step 17 — 一亩三分地本机采集（已确认）

`scripts/onepoint_collect.py`：`--from-dir` 读 fixture HTML 写出 note，不访问网络。线上被 Cloudflare / 未配置客户端时退出且不写坏 `index.json`。原始 HTML 只落 `data/raw/1p3a/`。

2026-08-23 本机实采多次被 Cloudflare 拦住。**暂时放弃线上抓取一亩三分地**；解析与流水线代码保留，不再实采。

## Step 18 — 一亩三分地进入同一流水线（已确认）

`run_pipeline` 可读 `source=1p3a` note（可重复 `--input-dir`）。fixture 里 Ada Ng 进主表，一亩三分地中介帖不进。详情原帖标签含「一亩三分地」。当前 `pytest`：67 passed。

## 研究方向 / 中介 audit

详情研究方向改为短 bullet。原帖用标题或日期。主表按更新时间倒序。留学咨询帖（踢我 / 避坑 / 推荐老师组）打成 agency。`run_pipeline` 写 `data/audit.json`。

## 详情页与访问量

访问量改为只显示本页 `page_pv`，未返回前隐藏。不蒜子 `site_pv` 按域名合计，会和 CityU-CS-Guide 混在一起并常卡住 Loading。原帖 URL 带 `xsec_token`。详情保留细分研究方向，邮箱/主页分行，取消学期。

## 抽取hotfix（自报姓名 / 中英对照）

本人招生帖里的「我是 X，即将加入 Y」只保留 X 和 Y。师从、指导、毕业单位里的教授不再进主表。`中文名（Prof. English）` 合并为一个人。

## 错挂修复（合作者 ≠ 招生老师）

「我是顾尚定，与 Dawn Song 合作，加入上交」只保留顾尚定 + 上海交通大学。导师为/合作者、URL 里的 berkeley.edu、目前就读的学校不再覆盖即将加入的单位。大陆学校地区为「中国大陆」。主表日期和地区列不再换行。

## 人名收紧

「X老师/教授」不再吞掉前面整段。只保留末尾 2–3 字且首字在常见姓氏里；「发邮件给 / 祝陈 / 和俞勇 / 创智学院」进 `weak_name` 不进主表。`audit.json` 增加 `weak_name` 与 `by_reason`。当前全量测试 68 passed。对 `data/raw/xhs` 重跑后主表约 20 行。

## 站点改版（Kami + 去重 + 取消校验 UI）

详情页改为一位老师一页：机会标签、学期并集、一条摘录、一组联系方式和原帖。首页与详情不再展示校验/冲突/学校核对。视觉对齐 Kami / CityU-CS-Guide token。
