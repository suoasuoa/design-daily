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
- 可选接入飞书群机器人，每天把最新 30 条选品情报推送到团队群。

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
-> 飞书群日报推送（可选）
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

默认每天北京时间 08:30、13:30、20:30 自动运行一次。每次都会尝试补足当天 30 条去重情报，并刷新页面。

也可以在 GitHub Actions 页面手动运行，并调整：

- `score_limit`：本轮最多评分多少个产品
- `search_jobs`：本轮跑多少个公开网页搜索任务

自动化成功后会把数据、周报和页面提交回 `main` 分支，并通过 GitHub Pages 发布。

## 飞书群推送

项目支持飞书“自定义机器人”群推送。配置后，GitHub Actions 每次生成最新日报时，会从当天 30 条情报里挑出最值得优先看的 5 个，推送到指定飞书群。

推送内容包括：

- 当天日期和完整数据池入口。
- 最推荐的 5 个选品，使用飞书卡片展示。
- 每条包含标题、品类、评分、来源、原链接。
- 每条自动生成一句推荐语，说明为什么值得看。

推荐语会参考这些标准：

```text
实用为先 / 高频需求 / 功能点清晰 / 打击面广 / 价格带大概率 >35 元 / 情绪或视觉钩子 / 来源可信度
```

### 配置方法

1. 在飞书群里添加“自定义机器人”。
2. 复制机器人 Webhook 地址。
3. 打开 GitHub 仓库 `Settings -> Secrets and variables -> Actions`。
4. 新增仓库 Secret：

```text
FEISHU_WEBHOOK_URL=飞书机器人 Webhook 地址
```

如果飞书机器人开启了“签名校验”，再新增：

```text
FEISHU_WEBHOOK_SECRET=飞书机器人签名密钥
```

没有配置 `FEISHU_WEBHOOK_URL` 时，推送脚本会自动跳过，不影响每日数据更新。

本地测试推送内容：

```bash
python3 scripts/push_feishu_daily.py --dry-run
```

本地真实推送：

```bash
FEISHU_WEBHOOK_URL="你的 webhook" python3 scripts/push_feishu_daily.py
```

## 社媒公开索引采集

项目会通过公开搜索索引补充社媒来源，不直接登录或操作社媒账号。

当前覆盖：

- 抖音公开视频页：`douyin.com/video`
- 小红书公开笔记页：`xiaohongshu.com/explore`、`xiaohongshu.com/discovery/item`
- Instagram 公开帖子页：`instagram.com/p`、`instagram.com/reel`

这类采集只保留具体内容页，搜索页、用户页、话题页、合集页会被过滤。进入数据池前还会按选品标准继续审核：

```text
实用为先 / 高频需求 / 功能点清晰 / 打击面广 / 价格带大概率 >35 元 / 3 秒看懂 / 情绪价值只能作为加分
```

社媒内容的口径会更开放一些：热度高、好看、有趣、种草、概念性产品、DIY/手作/改造内容都可以进入候选池，但必须能看出明确物件、明确使用场景，或对包装、结构、功能、外观有可转化启发。纯娱乐、纯生活记录、无明确物件的内容不会入池。

注意：公开索引不是平台内全量搜索，只能覆盖被搜索引擎收录的公开内容。它的定位是低风险社媒补充来源。

如果要提高社媒公开索引的稳定性，可以配置 Tavily 搜索 API：

```text
TAVILY_API_KEY
```

没有配置时，脚本会继续使用免费搜索页作为兜底，但覆盖率和稳定性会更弱。Tavily 只负责找候选链接，最终是否入池仍然由品类审核和选品评分决定。

## 本地社媒夜间采集（备用）

抖音、Instagram 这类社媒平台不适合放在 GitHub Actions 里直接采集。项目提供了一个本地桌面采集器，用你电脑上的可见浏览器，在登录状态下按品类搜索并保存线索。

这个方式容易遇到验证码或账号风控，目前只作为备用，不建议作为默认方案。第一版默认只采集抖音。Instagram 采集能力保留在脚本里，但不进入夜间定时任务，避免账号风险。

默认策略：

- 平台：抖音
- 时间：建议每天凌晨 00:30
- 目标：每天从抖音采集不少于 10 条社媒候选
- 方式：正常打开网页搜索，不绕过登录、验证码或平台限制
- 输出：`data/raw/social-desktop-YYYY-MM-DD.json`
- 后续：自动去重、审核、评分、构建网站，并推回 GitHub

第一次使用前安装 Playwright：

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

第一次建议先手动跑一遍，并在打开的浏览器里登录抖音：

```bash
python3 scripts/collect_desktop_social.py --platform douyin --target-total 20 --min-social 2
```

确认能采集后，运行完整夜间流程：

```bash
python3 scripts/nightly_social_update.py --target-total 80 --min-social 10
```

安装 macOS 每天凌晨 00:30 自动运行：

```bash
python3 scripts/install_nightly_social_launchd.py --hour 0 --minute 30
```

日志位置：

```text
logs/nightly-social.out.log
logs/nightly-social.err.log
```

如果某天抖音要求重新登录、验证码或安全验证，采集器会停在可见浏览器页面上。处理完后重新运行夜间流程即可。

## 这个工具适合怎么用

建议团队把它当作“选品会前的情报输入”：

1. 每天先看工作台里的“每日情报收集”日期分组。
2. 每周再看工作台里的“选品推荐组”100 条推荐。
3. 对感兴趣的内容进入原链接查看细节。
4. 按 `可直接买样 / 适合改造 / 方向参考` 决定下一步动作。
5. 人工筛选后再进入团队正式选品池。

这个项目负责扩大灵感来源、降低初筛成本、保持长期稳定收集；最终判断仍然交给团队完成。
