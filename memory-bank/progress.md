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

`.github/workflows/pages.yml` 用 fixture 建站后发 Pages。首页/详情/README 均有非官方声明。

当前 `pytest`：49 passed。

## 站点改版（Kami + 去重 + 取消校验 UI）

详情页改为一位老师一页：机会标签、学期并集、一条摘录、一组联系方式和原帖。首页与详情不再展示校验/冲突/学校核对。视觉对齐 Kami / CityU-CS-Guide token。
