# 🎯 Daily Design Digest

**创意设计每日情报系统** — 聚合全球设计灵感，数据每日 3 次自动累积。

🌐 **在线访问：** https://suoasuoa.github.io/design-daily/

---

## 🧠 核心选品标准

每一个收录的产品/项目，都遵循以下标准评估：

| # | 维度 | 说明 |
|---|------|------|
| 1 | **3秒看懂** | 直观好理解，看一眼就知道是啥 |
| 2 | **打击面广** | 大众高频需求，不是小众怪癖 |
| 3 | **有用** | 解决真实痛点，或提供情绪价值 |
| 4 | **还没泛滥** | 无大量山寨仿品，售价 > 35 RMB |
| 5 | **Wow!** | 让人惊叹的创意 |
| 6 | **反差** | 意料之外的设计巧思 |
| 7 | **幽默** | 会心一笑，有梗 |
| 8 | **温馨共鸣** | 戳中人心，有温度 |
| 9 | **实用为先** | 功能没短板，再叠加情绪价值 |

> 📌 **核心理念：** 先让产品功能没有短板，再叠加情绪价值。找打击面最广的内容。

---

## 📊 数据总览（共 918 条）

### 🏷️ 19 个品类

| 品类 | 数量 | 品类 | 数量 |
|------|------|------|------|
| 创意桌搭 | 130 | 创意礼盒 | 118 |
| 创意厨具 | 106 | 收纳包 | 71 |
| 氛围灯 | 68 | 冲锋衣 | 64 |
| 装置艺术 | 52 | 水杯 | 42 |
| 帽子 | 34 | 充电宝 | 31 |
| 卡包 | 27 | 卫衣 | 26 |
| T恤 | 26 | 端午礼盒 | 25 |
| 中秋礼盒 | 22 | 手机壳 | 21 |
| Polo衫 | 21 | 日历 | 17 |
| 钥匙扣水壶 | 17 |

### 🌐 11 个数据来源

| 来源 | 数量 | 数据真实性 |
|------|------|-----------|
| Good Design Award | 288 | ✅ 真实获奖数据 |
| Instagram | 159 | ⚠️ 含人工整理数据 |
| iF设计奖 | 118 | ✅ 真实获奖数据 |
| 小红书 | 99 | ⚠️ 含人工整理数据 |
| 抖音 | 76 | ⚠️ 含人工整理数据 |
| Red Dot | 63 | ⚠️ 含人工整理数据 |
| Pinterest | 43 | ⚠️ 含人工整理数据 |
| Behance | 35 | ⚠️ 含人工整理数据 |
| A' Design Award | 22 | ⚠️ 含人工整理数据 |
| Yanko Design | 8 | ✅ RSS 实时抓取 |
| Design Milk | 7 | ✅ RSS 实时抓取 |

> ✅ 真实性说明：Good Design Award 和 iF 设计奖为官方 API 真实获奖数据；RSS 源从 Design Milk / Dezeen / Yanko Design 实时抓取；其余来源为历史整理数据，后续逐步替换为实时采集。

---

## 🔄 自动积累管道

### 运行频率
每天 **3 次**自动运行（北京时间 08:00 / 16:00 / 00:00）

### 数据流
```
RSS 抓取 (Design Milk / Dezeen / Yanko Design)
  └→ 关键词匹配 → 分类到19个品类
  └→ 去重（按URL+标题）

G-Mark API 抓取
  └→ 品类映射 → 分类到19个品类
  └→ 去重（按奖项ID）

        ↓ 合并到 brand_pool.json

        ↓ generate.py

      data.js + data/latest.json → GitHub Pages
```

### 积累机制
- **RSS 文章：** 每次运行都抓最新文章，新文章自动加入 pool
- **G-Mark 获奖数据：** 每次运行都获取，但已存在的不会重复添加（按奖项 ID + URL 双重去重）
- **iF 设计奖：** 历史已抓取（需 Playwright 页面上下文，未来可能加入 GH Actions）

### 数据文件
- `brand_pool.json` — 主数据池，所有积累数据的唯一真相来源
- `accumulate.py` — 数据积累器（纯 Python，无额外依赖）
- `generate.py` — 从数据池生成前端数据文件
- `data.js` — GitHub Pages 加载的内嵌数据
- `data/latest.json` — 最新完整数据（JSON 格式）

---

## 🛠️ 技术栈

- **前端**：原生 HTML + CSS + JavaScript（无框架依赖）
- **数据**：Python 自动生成 + 积累
- **自动化**：GitHub Actions 每日 3 次定时更新
- **部署**：GitHub Pages
- **实时数据**：RSS 解析（urllib + xml.etree）+ G-Mark API
- **历史数据**：Good Design Award / iF 设计奖官方 API 抓取

## 📁 项目结构

```
design-daily/
├── index.html              # 前端页面
├── server.py               # 本地 HTTP 服务器
├── brand_pool.json         # 主数据池（积累的核心）
├── accumulate.py           # 数据积累器（RSS + G-Mark API）
├── generate.py             # 数据生成器 → data.js
├── scrape_full.py          # 全量爬虫（历史）
├── scrape_if.py            # iF 设计奖爬虫（Playwright）
├── scrape_gmark.py         # G-Mark 爬虫（Playwright）
├── data.js                 # GitHub Pages 版内嵌数据
├── data/
│   └── latest.json         # 最新数据
├── .github/workflows/
│   └── update.yml          # 每日 3 次积累 + 更新 Action
└── README.md
```

## 🚀 本地运行

```bash
# 1. 启动服务器
python3 server.py

# 2. 打开浏览器
open http://localhost:3456

# 3. 手动刷新数据
python3 generate.py

# 4. 手动累计新数据（测试用）
python3 accumulate.py --dry-run   # 预览新增
python3 accumulate.py             # 真实合并
```

## 🧩 待优化

- [ ] 加更多 RSS 源（Core77、Fast Company Design…）
- [ ] iF API 在 GH Actions 上走 Playwright 积累
- [ ] 小红书/抖音 Instagram 真实数据采集（需登录态）
- [ ] 选品评分自动过滤器（按核心标准打分量化为分数）

---

## 📄 许可证

MIT

---

*Made with ❤️ by SUOA*
