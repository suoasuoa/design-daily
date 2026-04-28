# 🎯 Daily Design Digest

**创意设计每日情报系统** — 聚合多平台设计灵感，每天自动更新。

## 🌐 在线访问

**https://suoasuoa.github.io/design-daily/**

> 数据由 GitHub Actions 每天 3 次（08:00 / 15:00 / 22:00 北京时间）自动更新。

## 📋 功能特点

- **7 大数据来源**：Good Design Award / iF设计奖 / Red Dot / A' Design Award / Instagram / 小红书 / 抖音
- **15 个设计品类**：水杯、氛围灯、日历、T恤、Polo衫、手机壳、创意厨具、卫衣、创意桌搭、卡包、钥匙扣水壶、冲锋衣、收纳包、充电宝、帽子
- **按来源筛选**：一键切换到特定平台的灵感
- **按品类筛选**：精准定位感兴趣的设计方向
- **关键词搜索**：搜索标题、品类、标签、来源
- **评分排序**：按热度/质量评分展示
- **每日更新**：每天 3 次自动刷新数据

## 🚀 本地运行

```bash
# 1. 启动服务器
python3 server.py

# 2. 打开浏览器
open http://localhost:3456

# 3. (可选) 手动刷新数据
python3 generate.py
```

## 🛠️ 技术栈

- **前端**：原生 HTML + CSS + JavaScript（无框架依赖）
- **后端**：Python HTTP Server（本地模式）
- **数据生成**：Python 自动生成
- **自动化**：GitHub Actions 定时更新
- **部署**：GitHub Pages

## 📁 项目结构

```
design-daily/
├── index.html          # 前端页面
├── server.py           # 本地 HTTP 服务器
├── generate.py         # 数据自动生成器
├── data.js             # GitHub Pages 版内嵌数据
├── data/
│   └── latest.json     # 最新数据
├── .github/workflows/
│   └── update.yml      # 定时更新 Action
└── README.md
```

## 📄 许可证

MIT

---

*Made with ❤️ by SUOA*
