# Design Daily — 设计灵感数据库

每日自动收集全球设计奖项与品牌案例，按 19 个品类分类展示。

🌐 **线上站点：** https://suoasuoa.github.io/design-daily/

📦 **数据量：** 1,089+ 条真实设计项目

🗂️ **数据来源：**
- iF 设计奖
- Good Design Award (G-Mark)
- Red Dot 设计奖
- A' Design Award
- Pinterest
- 小红书
- 抖音
- Instagram

🔄 **更新频率：** 每天 3 次（GitHub Actions 自动）

## 维护

修改数据前请查看 `CHECK.md`，里面有详细的部署检查清单和历史踩坑记录。

## Insight Pool MVP

新版产品线索池在 `insight/` 下生成，目标是长期积累可去重、可评分、可筛选的选品方向。

现在这套流程已经升级为“选品情报站”：每天收集公开来源和轮换的公开网页搜索结果，每周生成 100 条选品推荐。

```bash
python3 scripts/dedupe.py
python3 scripts/score.py --limit 200
python3 scripts/build_site.py
```

或直接运行智能体流程：

```bash
python3 scripts/agent_update.py --score-limit 200 --trend-limit 80
```

周报输出：

```text
insight/weekly.md
data/weekly_report.json
```

详情见 `INSIGHT_POOL.md`。

### 快速开始
```bash
# 重新生成前端数据
python3 generate.py

# 每日随机抽取
python3 generate.py --daily

# 指定数量随机
python3 generate.py --count=40
```
