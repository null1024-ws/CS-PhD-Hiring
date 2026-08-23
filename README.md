# CS-PhD-Hiring

从小红书收集 CS 相关老师的招生/招募信息（PhD、RA、实习等），做成可筛选的公开索引，方便发现「有这个老师」。

数据来自小红书社区，**非官方**。请以原帖和导师主页为准。

原始笔记、图片和登录 Cookie 只留在维护者本机，不会进这个仓库。

## 本地用 fixture 建站（无需登录小红书）

```powershell
pip install -r requirements.txt
python scripts/run_pipeline.py --input-dir tests/fixtures/notes
python scripts/build_site.py
start site/dist/index.html
```

跑测试：

```powershell
python -m pytest tests -q
```

## 采集真实小红书（维护者本机）

依赖 [xhs-cli](https://github.com/jackwener/xhs-cli)：

```powershell
pipx install xhs-cli
python -m camoufox fetch
xhs login
python scripts/xhs_collect.py --max-notes 3 --sleep 8
```

未登录时命令会提示 `xhs login` 并退出，不会写坏进度。

## 流水线

```
xhs_collect → data/raw/     原始笔记（gitignore）
OCR / bundle → 抽取 / 相关性 / 中介过滤 / 学校校验 / 去重
run_pipeline → data/listings.json + data/pis/
build_site   → site/dist/
```

学校字段会自动对照主页或公开资料；对不上仍展示，但标成「冲突」。科研中介帖即使写得很正常，只要正文（含图内 OCR）没有自己的邮箱/主页却在引导私信，就不会进主表。

## 补一条

用 GitHub Issue 模板「补充一条招募信息」。导入：

```powershell
python scripts/import_issue.py --issue-file path/to/issue.md
python scripts/run_pipeline.py
```

Issue 里自称的学校不会被直接标成已核对。
