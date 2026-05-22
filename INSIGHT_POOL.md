# Design Daily Insight Pool

这是新版 MVP：一个部署在 GitHub Pages 上的公开产品线索池，用来给团队提供选品方向。

## 核心原则

- 数据池优先，不先做复杂后台。
- 自动来源负责长期积累，小红书/抖音负责少量长期采样。
- 所有数据先去重，再评分，再发布到看板。
- 同一个产品在多个平台出现时合并为一个产品，保留多个来源记录。
- 评分优先级：实用、高频、打击面广、功能无短板、售价大于 35 RMB、3 秒看懂，最后再看情绪价值。

## 常用命令

```bash
python3 scripts/collect_public.py
python3 scripts/dedupe.py
python3 scripts/score.py --limit 200
python3 scripts/trend_agent.py --limit 80
python3 scripts/build_site.py
```

也可以直接运行每日智能体流程：

```bash
python3 scripts/agent_update.py --score-limit 200 --trend-limit 80
```

生成后打开：

```text
insight/index.html
```

## 小红书 / 抖音采样

默认每天每个平台每个品类最多 5 个采样槽位。

```bash
python3 scripts/collect_social.py --source xiaohongshu --per-category 5 --print-urls
python3 scripts/collect_social.py --source douyin --per-category 5 --print-urls
```

脚本会在 `data/raw/` 里创建模板文件。把你确认过的产品线索填进去，空白槽位会被 `dedupe.py` 忽略。

填完后运行：

```bash
python3 scripts/dedupe.py
python3 scripts/score.py --limit 200
python3 scripts/build_site.py
```

## DeepSeek

不要把 API Key 发到聊天里，也不要提交到 GitHub。复制 `.env.example` 为 `.env`：

```bash
cp .env.example .env
```

然后填入：

```bash
DEEPSEEK_API_KEY
DEEPSEEK_MODEL=deepseek-chat
```

本地脚本会自动读取 `.env`。

如果要让 GitHub Actions 使用 DeepSeek，在仓库设置里添加 Secret：

```text
DEEPSEEK_API_KEY
```

没有 Key 时，`scripts/score.py` 和 `scripts/trend_agent.py` 会用本地启发式评分/摘要，不会中断流程。

## GitHub Pages

第一版看板输出到：

```text
insight/index.html
insight/data.json
```

如果 Pages 仍然从仓库根目录发布，新看板地址通常是：

```text
https://suoasuoa.github.io/design-daily/insight/
```
