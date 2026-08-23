# Tech Stack — CS-PhD-Hiring

原则：能静态就静态，能复用 CityU-CS-Guide 已验证的工具就不换新栈。不为表格页引入前端框架。

## Application / site

- **静态 HTML + 少量原生 JS**
  - 首页表格筛选在浏览器里对一份 JSON 过滤即可，体量按千级行设计。
  - 详情页由构建脚本输出独立 HTML。
  - 理由：无后端、GitHub Pages 可托管、和 DuoOffer 的「一张表」一致。
- **视觉**
  - 详情页沿用 CityU-CS-Guide / Kami 的纸感（暖纸底、墨蓝、衬线层级）。
  - 首页表格以清晰筛选为先，不把整站做成重设计。

## Backend / runtime

- **Python 3.11+**
  - 采集、OCR、抽取、校验、建站都是脚本，和 CityU-CS-Guide 同一运行时。
  - 无常驻服务。

## Collection

- **[xhs-cli](https://github.com/jackwener/xhs-cli) + Camoufox**
  - CityU-CS-Guide 已验证：浏览器模式比逆向 API 稳，支持 search / read --comments、断点、限速。
  - 登录态只存在维护者本机 `~/.xhs-cli/`。

## Storage

- **JSON 文件**
  - `data/schools.json`：学校别名。
  - `data/listings.json`、`data/pis/`：发布数据。
  - `data/raw/`：本机原始抓取，gitignore。
  - 理由：无需数据库；PR 可审；静态站直接读 JSON。

## School verification

- **学校别名表**（手维护 JSON）：港科大 / HKUST / 香港科技大学 → 同一规范名 + 国家。
- **主页抓取**：`httpx` 拉公开 HTML，只做文本比对。
- **OpenAlex API**：用老师名查近期 affiliation，免费、无需密钥。
- 不在 v1 引入付费搜索或浏览器自动化去「搜老师」。

## Auth

- 站点无登录。
- 采集登录：维护者本机 `xhs login`。
- 补条：GitHub 账号提 Issue，不自建账号系统。

## Deployment

- **GitHub Pages**
  - `scripts/build_site.py` 输出到 `site/dist/`。
  - `main` 推送后 Actions 发布。
  - 理由：和 DuoOffer、CityU-CS-Guide 相同，零运维。

## Testing

- **pytest**
  - fixture 驱动：抽取、学校规范化、冲突/一致校验、去重、CS 过滤、Issue 导入。
  - 一条「无小红书登录」的本地建站冒烟：fixture → listings → `index.html`。
- 不做在线抓取的 CI（避免登录和风控）。

## Explicitly not chosen

- Next.js / React / 数据库：对筛选表格过重。
- 在线 LLM 抽取：增加密钥和费用，v1 用规则 + 别名表；准确率靠校验和 GitHub 纠错。
- 自建爬虫：不重复造轮子，沿用 `xhs-cli`。
