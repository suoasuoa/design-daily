# Design Daily

Design Daily 是给选品团队使用的自动化创意情报工具。它持续发现真实产品和设计案例，经过去重、页面校验与 AI 审核后，每个工作日留下 40 条可供人工筛选的选品方向。

- [线上选品情报工作台](https://suoasuoa.github.io/design-daily/insight/)

## 核心能力

- 周一至周五分三阶段收集，逐步完成 `15 -> 30 -> 40` 条新选品；周末不运行。
- DeepSeek V4 Flash 根据当日缺口、品类分布和历史结果动态规划搜索词。
- 真实搜索后端负责返回网页，DeepSeek 不生成产品链接。
- 只保留白名单来源中的具体产品页或具体案例页，过滤搜索页、合集页和泛文章。
- 校验页面标题、摘要、主图和 canonical URL，图片无法确认时允许留空，链接必须可追溯。
- 对 URL、标题、产品指纹和历史淘汰池去重，同一产品不会换日期重复出现。
- DeepSeek 先做候选预筛，再由严格品类审核做终审；数量不足时自动换角度继续搜索。
- 每周从完整池中生成 100 条去重推荐，并在飞书群推送当天 Top 5。

## 选品标准

内容必须先属于目标品类，再判断是否值得进入数据池。

```text
1. 实用为先，解决明确问题
2. 高频需求，覆盖人群足够广
3. 功能成立且没有明显短板
4. 有结构、功能、材料、交互或使用场景创新
5. 预估售价大于 35 RMB
6. 三秒能看懂产品与核心卖点
7. 情绪价值只能在功能成立后加分
```

普通基础款、只换颜色/图案、普通联名、无法确认具体产品、链接指向搜索结果或品类集合的内容会被拒绝。

## 当前品类

```text
水杯 / 氛围灯 / 创意礼盒 / 装置艺术 / 创意厨具
中秋礼盒 / 创意桌搭 / 端午礼盒 / 充电宝 / 日历
手机壳 / 冲锋衣 / 钥匙扣水壶
```

`T恤、帽子、卫衣、Polo衫、收纳包、卡包` 已于 2026-07-16 停止新增，历史内容仍保留在归档中。

品类边界与审核规则统一配置在 `scripts/insight_config.py`。

## 自动流程

```text
RSS/精选页面采集
-> DeepSeek 分析当日缺口并规划搜索词
-> 免费搜索后端执行真实网页搜索
-> 白名单与详情页过滤
-> 页面标题/摘要/主图校验
-> DeepSeek 候选预筛
-> 全库去重
-> DeepSeek 严格品类终审
-> 不足 40 条时换搜索角度继续补量
-> 评分、趋势与周报
-> GitHub Pages 更新
-> 飞书 Top 5 推送
```

搜索审计会写入 `data/reports/deepseek-search-agent-YYYY-MM-DD.json`，可以看到每一轮的搜索词数量、真实结果数、预筛数、保留数和品类分布。

## 数据来源

主池优先使用可追溯的设计奖项、专业设计媒体、包装网站、设计社区、众筹和高质量商品案例，包括：

```text
Good Design Award / iF / Red Dot / IDEA / DIA
Dezeen / Design Milk / Yanko Design / Core77 / Designboom / DesignWanted
The Dieline / Packaging of the World / Pentawards / BP&O / Lovely Package
站酷 / 普象网 / 设计癖 / 数英 / Behance
Kickstarter / Indiegogo / Uncrate / Cool Material / Gear Patrol
```

弱来源会被降权；Etsy 搜索页、标签页、集合页不会进入主池。社媒自动采集目前关闭，后续应作为独立待筛池接入。

## 每日时间

GitHub Actions 仅在周一至周五按北京时间运行：

- `07:30`：第一阶段，目标累计 15 条。
- `11:30`：第二阶段，目标累计 30 条。
- `15:30`：第三阶段，目标累计 40 条。
- 每个阶段约 40 分钟后有一次漏跑检查，已经达标则自动跳过。
- `17:00` 起飞书每 10 分钟检查一次，满 40 条后推送 Top 5；`18:00` 是强制检查点，但仍必须满 40 条。
- 周六、周日不收集、不更新当日分组，也不发送飞书。

三个阶段只收集数据库里从未出现过的新内容，不会把旧池内容改成今天日期。

## 本地运行

复制环境变量文件并填写 DeepSeek API Key：

```bash
cp .env.example .env
```

```text
DEEPSEEK_API_KEY=你的 API Key
DEEPSEEK_MODEL=deepseek-v4-flash
```

安装免费搜索后端并完整运行：

```bash
python3 -m pip install ddgs
python3 scripts/agent_update.py --daily-target 40 --agent-queries 90 --agent-pages 420
```

只运行一轮 DeepSeek 搜索智能体：

```bash
python3 scripts/search_jobs.py
python3 scripts/deepseek_search_agent.py --target 40 --query-count 90 --per-query 10 --max-pages 420
```

只生成和预览页面：

```bash
python3 scripts/build_site.py
python3 -m http.server 8765
```

打开 `http://127.0.0.1:8765/insight/`。

## GitHub 配置

仓库 `Settings -> Secrets and variables -> Actions` 至少需要：

```text
DEEPSEEK_API_KEY
```

可选配置：

```text
FEISHU_WEBHOOK_URL
FEISHU_WEBHOOK_SECRET
SEARXNG_BASE_URL
TAVILY_API_KEY
```

日常搜索优先使用自托管 SearXNG 或免费的 `ddgs`，Tavily 默认关闭。DeepSeek API 缺失时只能退回固定搜索词，无法执行 AI 预筛，因此正式自动化必须配置 `DEEPSEEK_API_KEY`。

手动运行 `.github/workflows/insight-pool.yml` 时可以调整：

- `score_limit`：本轮最多评分多少条。
- `agent_queries`：DeepSeek 每轮规划多少条搜索词。
- `agent_pages`：每轮最多读取并预筛多少个新页面。
- `use_tavily`：是否临时启用 Tavily，默认关闭。

自动化会提交数据与静态页面到 `main`，GitHub Pages 随后更新。

## 主要文件

```text
scripts/deepseek_search_agent.py       DeepSeek 搜索智能体
scripts/review_categories.py           严格品类终审
scripts/ensure_daily_minimum.py         工作日 40 条补量循环
scripts/insight_config.py               品类、来源与选品规则
data/products.json                      当前严格通过的产品池
data/rejected_category.json             淘汰归档
data/reports/                            搜索与清理审计
insight/index.html                       选品工作台
```

## 飞书推送

配置 `FEISHU_WEBHOOK_URL` 后，飞书工作流会从工作日当天 40 条中选择综合评分最高的 5 条，以卡片形式发送标题、品类、推荐指数、推荐理由、图片和原链接。没有可靠图片时不展示图片，不会用其他产品图片代替。
