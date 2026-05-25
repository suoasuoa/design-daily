# Design Daily

Design Daily 是一个面向选品团队的自动化选品情报工具。

它不是传统意义上的设计图库，也不是把所有链接堆在一起的数据仓库。它的目标是持续从公开来源里发现产品线索，经过去重、品类审核、AI 评分和趋势分析后，每周生成一份可以直接进入选品会讨论的推荐清单。

线上入口：

- [选品情报工作台](https://suoasuoa.github.io/design-daily/insight/)

## 它能做什么

- 每天自动收集公开设计媒体、产品媒体和网页搜索结果。
- 按 19 个重点品类持续搜索新品、创意、包装、结构和趋势信号。
- 自动合并重复产品，避免同一个产品反复入池。
- 用 AI 审核内容是否真的属于目标品类。
- 按选品标准给产品打分：实用、高频、打击面广、功能完整、价格大于 35 RMB、3 秒看懂、情绪价值。
- 把内容分成 `可直接买样`、`适合改造`、`方向参考` 三条路径。
- 每周生成 100 条选品推荐，给团队做人工筛选和选品讨论。
- 每天生成一个日期分组，默认展示当天前 30 条去重情报。

## 工作流

```text
公开来源采集
-> 搜索任务矩阵
-> 原始线索池
-> 去重合并
-> 品类审核
-> AI 评分
-> 趋势分析
-> 周报 100 条推荐
-> GitHub Pages 工作台
```

## 数据来源

当前自动化来源包括两类。

公开内容源：

- Dezeen
- Design Milk
- Yanko Design

公开网页搜索：

- 按 19 个品类生成中英文搜索任务
- 覆盖产品新品、包装设计、众筹平台、趋势媒体、品牌和电商参考
- 搜索结果先进入原始线索池，再经过 AI 审核和去重

社交平台如小红书、抖音、视频号、Instagram 更适合人工或半自动采样。这个项目已经保留了采样入口，但不会在 GitHub Actions 里直接爬取这些平台。

## 选品品类

当前重点品类：

```text
水杯 / 氛围灯 / 创意礼盒 / 装置艺术 / 创意厨具 / 中秋礼盒 / 帽子
创意桌搭 / 端午礼盒 / 充电宝 / 日历 / T恤 / 卫衣 / 卡包
手机壳 / 收纳包 / Polo衫 / 冲锋衣 / 钥匙扣水壶
```

品类和搜索关键词配置在：

```text
scripts/insight_config.py
```

## 输出内容

主要输出：

```text
insight/index.html       选品情报工作台
insight/data.json        前端数据
insight/weekly.md        本周推荐的 Markdown 备用导出
insight/weekly.json      周报结构化数据
```

数据文件：

```text
data/raw/                原始采集结果
data/products.json       去重后的产品池
data/search_jobs.json    搜索任务矩阵
data/trends.json         趋势报告
data/weekly_report.json  当前周报
data/reports/            历史周报
```

## 本地运行

完整运行一次自动化流程：

```bash
python3 scripts/agent_update.py --score-limit 200 --trend-limit 100 --weekly-limit 100
```

只重新生成页面：

```bash
python3 scripts/build_site.py
```

本地预览：

```bash
python3 -m http.server 8765
```

然后打开：

```text
http://127.0.0.1:8765/insight/
```

## 分步命令

```bash
python3 scripts/collect_public.py
python3 scripts/search_jobs.py
python3 scripts/collect_search.py --limit-jobs 40 --per-job 4
python3 scripts/dedupe.py
python3 scripts/review_categories.py --batch-size 20
python3 scripts/score.py --limit 200
python3 scripts/trend_agent.py --limit 100
python3 scripts/build_site.py
python3 scripts/weekly_report.py --limit 100
python3 scripts/build_site.py
```

## DeepSeek 配置

本地使用时可以复制 `.env.example`：

```bash
cp .env.example .env
```

然后填入：

```text
DEEPSEEK_API_KEY=你的 API Key
DEEPSEEK_MODEL=deepseek-chat
```

GitHub Actions 使用仓库 Secret：

```text
DEEPSEEK_API_KEY
```

没有 API Key 时，部分脚本会退回本地启发式逻辑，流程不会中断，但 AI 判断质量会下降。

## GitHub Actions

工作流文件：

```text
.github/workflows/insight-pool.yml
```

默认每天北京时间 09:20 自动运行一次。

也可以在 GitHub Actions 页面手动运行，并调整：

- `score_limit`：本轮最多评分多少个产品
- `search_jobs`：本轮跑多少个公开网页搜索任务

自动化成功后会把数据、周报和页面提交回 `main` 分支，并通过 GitHub Pages 发布。

## 这个工具适合怎么用

建议团队把它当作“选品会前的情报输入”：

1. 每天先看工作台里的“每日情报收集”日期分组。
2. 每周再看工作台里的“选品推荐组”100 条推荐。
3. 对感兴趣的内容进入原链接查看细节。
4. 按 `可直接买样 / 适合改造 / 方向参考` 决定下一步动作。
5. 人工筛选后再进入团队正式选品池。

这个项目负责扩大灵感来源、降低初筛成本、保持长期稳定收集；最终判断仍然交给团队完成。
