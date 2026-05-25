#!/usr/bin/env python3
"""Build a selection-team-oriented inspiration workspace."""

from collections import Counter, defaultdict
import json

from insight_common import DATA_DIR, INSIGHT_DIR, ensure_dirs, load_json, now_iso, write_json


FUNCTION_WORDS = [
    "便携", "portable", "防水", "waterproof", "收纳", "storage", "模块", "modular",
    "充电", "charge", "磁吸", "magnetic", "折叠", "foldable", "多功能", "multifunction",
]
PACKAGING_WORDS = [
    "包装", "packaging", "box", "gift", "礼盒", "套装", "mooncake", "中秋", "端午",
]
STRUCTURE_WORDS = [
    "结构", "structure", "支架", "frame", "fold", "hinge", "assembly", "模块", "shelf",
]
EMOTION_WORDS = [
    "可爱", "cute", "温暖", "warm", "治愈", "playful", "surprise", "惊喜", "趣味", "幽默", "氛围",
]
VISUAL_WORDS = [
    "纹理", "texture", "color", "颜色", "graphic", "图形", "surface", "材质", "finish",
]


def sorted_products(products):
    return sorted(
        products,
        key=lambda item: (
            int(item.get("selection_score") or 0),
            int(item.get("seen_count") or 0),
            item.get("last_seen") or "",
        ),
        reverse=True,
    )


def hits(text, words):
    text = text.lower()
    return sum(1 for word in words if word.lower() in text)


def source_family(item):
    source = (item.get("sources") or [{}])[0]
    source_type = source.get("source_type", "")
    if source_type == "social_signal":
        return "社交灵感"
    if source_type == "verified_official":
        return "奖项案例"
    if source_type == "editorial_source":
        return "媒体案例"
    return "其他来源"


def action_lane(item):
    category = item.get("category", "")
    source = (item.get("sources") or [{}])[0]
    source_type = source.get("source_type", "")
    price_gate = item.get("price_gate")
    score = int(item.get("selection_score") or 0)
    text = " ".join(
        [
            item.get("title", ""),
            item.get("summary", ""),
            " ".join(item.get("tags", [])),
            " ".join(item.get("trend_tags", [])),
        ]
    ).lower()

    if source_type == "social_signal" and price_gate == "likely_over_35" and score >= 60:
        return "可直接买样"
    if category in {"创意礼盒", "中秋礼盒", "端午礼盒", "创意厨具", "创意桌搭", "手机壳", "水杯"}:
        return "适合改造"
    if hits(text, PACKAGING_WORDS) >= 2 or category in {"创意礼盒", "中秋礼盒", "端午礼盒"}:
        return "适合改造"
    if source_type == "verified_official" or source_type == "editorial_source":
        return "方向参考"
    return "适合改造"


def inspiration_axes(item):
    text = " ".join(
        [
            item.get("title", ""),
            item.get("summary", ""),
            " ".join(item.get("tags", [])),
            " ".join(item.get("trend_tags", [])),
        ]
    ).lower()
    axes = []
    if hits(text, FUNCTION_WORDS) >= 1 or item.get("category") in {"创意厨具", "充电宝", "水杯", "收纳包"}:
        axes.append("功能启发")
    if hits(text, PACKAGING_WORDS) >= 1 or item.get("category") in {"创意礼盒", "中秋礼盒", "端午礼盒"}:
        axes.append("包装启发")
    if hits(text, STRUCTURE_WORDS) >= 1 or item.get("category") in {"创意桌搭", "装置艺术", "收纳包"}:
        axes.append("结构启发")
    if hits(text, EMOTION_WORDS) >= 1 or item.get("category") in {"氛围灯", "帽子"}:
        axes.append("情绪启发")
    if hits(text, VISUAL_WORDS) >= 1 or not axes:
        axes.append("视觉启发")
    return axes[:3]


def image_state(item):
    image = item.get("image", "")
    title = item.get("title", "").lower()
    if not image:
        return "缺图"
    review = item.get("category_review") or {}
    reason = (review.get("reason") or "").lower()
    if "图" in reason and ("不符" in reason or "不一致" in reason):
        return "待核图"
    if "packaging" in image.lower() and item.get("category") == "冲锋衣":
        return "待核图"
    if "image" in title or "render" in title:
        return "待核图"
    return "已对齐"


def record(item):
    source = (item.get("sources") or [{}])[0]
    axes = inspiration_axes(item)
    lane = action_lane(item)
    review = item.get("category_review") or {}
    return {
        "id": item.get("id"),
        "title": item.get("title", ""),
        "category": item.get("category", ""),
        "summary": item.get("ai_reason") or item.get("summary", ""),
        "score": int(item.get("selection_score") or 0),
        "price_gate": item.get("price_gate", "unknown"),
        "image": item.get("image", ""),
        "url": item.get("url") or source.get("url") or "#",
        "source_name": source.get("source", item.get("source_primary", "未知来源")),
        "source_family": source_family(item),
        "source_type": source.get("source_type", ""),
        "action_lane": lane,
        "axes": axes,
        "image_state": image_state(item),
        "seen_count": int(item.get("seen_count") or 0),
        "last_seen": item.get("last_seen", ""),
        "review_reason": review.get("reason", ""),
        "review_confidence": review.get("confidence", 0),
        "tags": (item.get("trend_tags") or [])[:4] + [tag for tag in (item.get("tags") or [])[:6] if tag not in (item.get("trend_tags") or [])][:2],
    }


def build_payload(products, trends, weekly_report=None):
    items = [record(item) for item in sorted_products(products)]
    by_category = Counter(item["category"] for item in items)
    by_lane = Counter(item["action_lane"] for item in items)
    by_axis = Counter(axis for item in items for axis in item["axes"])
    by_source_family = Counter(item["source_family"] for item in items)
    by_image_state = Counter(item["image_state"] for item in items)

    lane_top = {}
    for lane in ["可直接买样", "适合改造", "方向参考"]:
        lane_top[lane] = [item for item in items if item["action_lane"] == lane][:12]

    axis_top = {}
    for axis in ["功能启发", "包装启发", "结构启发", "情绪启发", "视觉启发"]:
        axis_top[axis] = [item for item in items if axis in item["axes"]][:12]

    return {
        "generated_at": now_iso(),
        "stats": {
            "total_items": len(items),
            "by_category": dict(by_category.most_common()),
            "by_lane": dict(by_lane.most_common()),
            "by_axis": dict(by_axis.most_common()),
            "by_source_family": dict(by_source_family.most_common()),
            "by_image_state": dict(by_image_state.most_common()),
        },
        "trends": trends,
        "weekly_report": weekly_report or {},
        "featured": {
            "lanes": lane_top,
            "axes": axis_top,
        },
        "items": items,
    }


HTML = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Selection Signal Desk</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Manrope:wght@500;700;800&family=Noto+Sans+SC:wght@400;500;700;800&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #f4f6f8;
      --panel: rgba(255, 255, 255, 0.92);
      --card: #ffffff;
      --ink: #23211c;
      --muted: #667085;
      --line: rgba(35, 45, 60, 0.12);
      --accent: #d66b2c;
      --accent-deep: #9c4b1c;
      --sage: #4f8063;
      --mustard: #d5a540;
      --sky: #527fa3;
      --shadow: 0 18px 40px rgba(31, 41, 55, 0.08);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Manrope", "Noto Sans SC", sans-serif;
      color: var(--ink);
      background:
        linear-gradient(135deg, rgba(82,127,163,0.10), transparent 34%),
        linear-gradient(315deg, rgba(214,107,44,0.08), transparent 30%),
        linear-gradient(180deg, #f8fafc 0%, var(--bg) 100%);
      min-height: 100vh;
    }
    .shell {
      width: min(1520px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 28px 0 48px;
    }
    .hero {
      display: grid;
      grid-template-columns: 1.2fr 0.8fr;
      gap: 22px;
      align-items: stretch;
    }
    .hero-main, .hero-side, .panel, .card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 24px;
      backdrop-filter: blur(10px);
      box-shadow: var(--shadow);
    }
    .hero-main {
      padding: 30px 30px 26px;
      overflow: hidden;
      position: relative;
    }
    .hero-main:before {
      content: "";
      position: absolute;
      inset: 0;
      background:
        linear-gradient(135deg, rgba(82,127,163,0.14), transparent 40%),
        linear-gradient(315deg, rgba(214,107,44,0.12), transparent 38%);
      pointer-events: none;
    }
    .eyebrow {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
      font-weight: 800;
      color: var(--accent-deep);
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }
    .eyebrow span {
      width: 10px;
      height: 10px;
      border-radius: 999px;
      background: var(--accent);
    }
    h1 {
      margin: 18px 0 10px;
      font-size: clamp(34px, 6vw, 66px);
      line-height: 0.98;
      letter-spacing: -0.03em;
      max-width: 10ch;
    }
    .lead {
      margin: 0;
      max-width: 48ch;
      color: var(--muted);
      font-size: 16px;
      line-height: 1.65;
      position: relative;
      z-index: 1;
    }
    .hero-stats {
      margin-top: 22px;
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      position: relative;
      z-index: 1;
    }
    .hero-stat {
      background: rgba(255,255,255,0.7);
      border: 1px solid rgba(84, 70, 52, 0.1);
      border-radius: 18px;
      padding: 14px;
      min-height: 94px;
    }
    .hero-stat strong {
      display: block;
      font-size: 28px;
      line-height: 1;
    }
    .hero-stat span {
      display: block;
      margin-top: 8px;
      font-size: 12px;
      color: var(--muted);
      font-weight: 700;
    }
    .hero-side {
      padding: 24px;
      display: grid;
      gap: 18px;
    }
    .side-block h2 {
      margin: 0 0 12px;
      font-size: 15px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
    }
    .chips {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
    .chip {
      display: inline-flex;
      align-items: center;
      min-height: 34px;
      padding: 0 12px;
      border-radius: 999px;
      background: #fff;
      border: 1px solid var(--line);
      font-size: 13px;
      font-weight: 700;
      color: var(--ink);
      cursor: pointer;
    }
    .chip.active {
      background: var(--accent);
      border-color: var(--accent);
      color: #fff;
    }
    .chip.muted {
      cursor: default;
    }
    .toolbar {
      margin-top: 18px;
      display: grid;
      grid-template-columns: minmax(240px, 1fr) auto;
      gap: 14px;
      align-items: center;
    }
    .search {
      display: flex;
      align-items: center;
      gap: 10px;
      height: 54px;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 0 16px;
      box-shadow: var(--shadow);
    }
    .search input {
      width: 100%;
      border: 0;
      outline: 0;
      background: transparent;
      font: inherit;
      font-size: 16px;
      color: var(--ink);
    }
    .timestamp {
      color: var(--muted);
      font-size: 13px;
      font-weight: 700;
      white-space: nowrap;
    }
    .grid-section {
      margin-top: 26px;
      display: grid;
      grid-template-columns: 1.15fr 0.85fr;
      gap: 22px;
      align-items: start;
    }
    .panel {
      padding: 20px;
    }
    .panel h3 {
      margin: 0 0 14px;
      font-size: 22px;
      letter-spacing: -0.02em;
    }
    .lane-row {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      margin-top: 10px;
    }
    .lane-card {
      border-radius: 20px;
      padding: 16px;
      min-height: 150px;
      color: #fff;
      cursor: pointer;
      transition: transform .18s ease;
    }
    .lane-card:hover { transform: translateY(-2px); }
    .lane-card.buy { background: linear-gradient(135deg, #cf6f39, #edb24c); }
    .lane-card.adapt { background: linear-gradient(135deg, #6d8d76, #9db58f); }
    .lane-card.reference { background: linear-gradient(135deg, #5b7989, #8fb2c2); }
    .lane-card strong {
      display: block;
      font-size: 14px;
      opacity: 0.9;
    }
    .lane-card em {
      display: block;
      margin-top: 10px;
      font-style: normal;
      font-size: 32px;
      line-height: 1;
      font-weight: 800;
    }
    .lane-card p {
      margin: 12px 0 0;
      font-size: 13px;
      line-height: 1.5;
      opacity: 0.94;
    }
    .trend-list, .queue-list {
      display: grid;
      gap: 10px;
    }
    .trend-item, .queue-item {
      display: grid;
      gap: 5px;
      border-top: 1px solid var(--line);
      padding-top: 10px;
    }
    .trend-item:first-child, .queue-item:first-child {
      border-top: 0;
      padding-top: 0;
    }
    .trend-item strong, .queue-item strong {
      font-size: 15px;
    }
    .trend-item span, .queue-item span {
      color: var(--muted);
      font-size: 13px;
      line-height: 1.55;
    }
    .filters {
      margin-top: 24px;
      display: grid;
      gap: 12px;
    }
    .filter-row {
      display: grid;
      gap: 8px;
    }
    .filter-row strong {
      font-size: 13px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
    }
    .card-grid {
      margin-top: 24px;
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 18px;
    }
    .card {
      overflow: hidden;
      background: var(--card);
      border-radius: 22px;
      border: 1px solid var(--line);
      box-shadow: var(--shadow);
      display: flex;
      flex-direction: column;
    }
    .thumb {
      width: 100%;
      aspect-ratio: 1.08 / 0.84;
      object-fit: cover;
      background: linear-gradient(135deg, #e6edf3, #f8fafc);
    }
    .body {
      padding: 16px;
      display: grid;
      gap: 10px;
      flex: 1;
    }
    .meta {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }
    .pill {
      display: inline-flex;
      align-items: center;
      min-height: 26px;
      padding: 0 10px;
      border-radius: 999px;
      background: #fff4e8;
      color: var(--accent-deep);
      font-size: 11px;
      font-weight: 800;
      border: 1px solid rgba(200,99,42,0.12);
    }
    .pill.sage { background: #edf5ee; color: #507155; border-color: rgba(108,136,112,0.16); }
    .pill.sky { background: #edf5f8; color: #4c6c7b; border-color: rgba(109,149,167,0.16); }
    .pill.gray { background: #f5f2ec; color: #6b645b; border-color: rgba(84,70,52,0.1); }
    .title {
      margin: 0;
      font-size: 28px;
      line-height: 1.06;
      letter-spacing: -0.03em;
    }
    .title a { color: inherit; text-decoration: none; }
    .title a:hover { color: var(--accent-deep); }
    .summary {
      margin: 0;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.62;
      min-height: 68px;
    }
    .scoreline {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }
    .score {
      font-size: 30px;
      font-weight: 800;
      line-height: 1;
    }
    .source {
      color: var(--muted);
      font-size: 13px;
      font-weight: 700;
      text-align: right;
    }
    .tags {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }
    .empty {
      margin-top: 24px;
      padding: 40px 20px;
      background: var(--panel);
      border: 1px dashed var(--line);
      border-radius: 20px;
      text-align: center;
      color: var(--muted);
      font-weight: 700;
    }
    @media (max-width: 1100px) {
      .hero, .grid-section { grid-template-columns: 1fr; }
    }
    @media (max-width: 760px) {
      .shell { width: min(100vw - 20px, 1520px); padding-top: 16px; }
      .hero-main, .hero-side, .panel { padding: 18px; }
      .hero-stats, .lane-row { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .toolbar { grid-template-columns: 1fr; }
      .title { font-size: 24px; }
      .card-grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <div class="hero-main">
        <div class="eyebrow"><span></span>Selection Signal Desk</div>
        <h1>给选品团队看的灵感工作台</h1>
        <p class="lead">这版不再把所有内容塞进一个杂池里，而是先回答三件事：这条东西适不适合买样、值不值得改造、它给我们的启发更偏功能、包装、结构还是情绪。</p>
        <div class="hero-stats" id="heroStats"></div>
      </div>
      <aside class="hero-side">
        <div class="side-block">
          <h2>当前热点</h2>
          <div class="chips" id="topAxisChips"></div>
        </div>
        <div class="side-block">
          <h2>来源结构</h2>
          <div class="chips" id="sourceFamilyChips"></div>
        </div>
        <div class="side-block">
          <h2>图片状态</h2>
          <div class="chips" id="imageStateChips"></div>
        </div>
      </aside>
    </section>

    <section class="toolbar">
      <label class="search">
        <span>⌕</span>
        <input id="search" type="search" placeholder="搜索标题、品类、启发方式、来源...">
      </label>
      <div class="timestamp" id="timestamp"></div>
    </section>

    <section class="grid-section">
      <div class="panel">
        <h3>本周优先看</h3>
        <div class="lane-row" id="laneCards"></div>
      </div>
      <div class="panel">
        <h3>趋势摘要</h3>
        <div class="trend-list" id="trendList"></div>
      </div>
    </section>

    <section class="filters">
      <div class="filter-row">
        <strong>动作路径</strong>
        <div class="chips" id="laneFilters"></div>
      </div>
      <div class="filter-row">
        <strong>启发类型</strong>
        <div class="chips" id="axisFilters"></div>
      </div>
      <div class="filter-row">
        <strong>品类</strong>
        <div class="chips" id="categoryFilters"></div>
      </div>
      <div class="filter-row">
        <strong>来源分层</strong>
        <div class="chips" id="sourceFilters"></div>
      </div>
    </section>

    <section class="panel" style="margin-top:24px;">
      <h3>推荐队列</h3>
      <div class="queue-list" id="queueList"></div>
    </section>

    <section class="card-grid" id="cardGrid"></section>
    <div class="empty" id="emptyState" hidden>当前筛选下没有内容。</div>
  </div>

  <script src="./data.json"></script>
  <script>
    const payload = window.__INSIGHT_DATA__;
    const state = {
      q: "",
      lane: "全部",
      axis: "全部",
      category: "全部",
      source: "全部"
    };
    const $ = id => document.getElementById(id);

    function num(v) { return Number(v || 0); }

    function timestampText(value) {
      const date = new Date(value.replace(" ", "T"));
      if (Number.isNaN(date.getTime())) return value;
      return `最近生成 ${date.toLocaleString("zh-CN", { hour12: false })}`;
    }

    function cardClass(lane) {
      if (lane === "可直接买样") return "buy";
      if (lane === "适合改造") return "adapt";
      return "reference";
    }

    function chip(label, active, onClick, extraClass = "") {
      const el = document.createElement("button");
      el.type = "button";
      el.className = `chip ${extraClass}`.trim();
      if (active) el.classList.add("active");
      el.textContent = label;
      if (onClick) el.addEventListener("click", onClick);
      else el.classList.add("muted");
      return el;
    }

    function renderHero() {
      const total = payload.stats.total_items;
      const byLane = payload.stats.by_lane;
      const weeklyCount = (payload.weekly_report && payload.weekly_report.actual_count) || 0;
      const stats = [
        [total, "当前可看灵感"],
        [weeklyCount, "本周推荐"],
        [byLane["可直接买样"] || 0, "可直接买样"],
        [byLane["适合改造"] || 0, "适合改造"]
      ];
      $("heroStats").innerHTML = stats.map(([value, label]) => `<div class="hero-stat"><strong>${value}</strong><span>${label}</span></div>`).join("");
      $("timestamp").textContent = timestampText(payload.generated_at);

      const topAxis = Object.entries(payload.stats.by_axis).slice(0, 6);
      $("topAxisChips").innerHTML = "";
      topAxis.forEach(([name, count]) => $("topAxisChips").appendChild(chip(`${name} ${count}`, false, null, "gray")));

      const families = Object.entries(payload.stats.by_source_family);
      $("sourceFamilyChips").innerHTML = "";
      families.forEach(([name, count]) => $("sourceFamilyChips").appendChild(chip(`${name} ${count}`, false, null, "gray")));

      const imageStates = Object.entries(payload.stats.by_image_state);
      $("imageStateChips").innerHTML = "";
      imageStates.forEach(([name, count]) => $("imageStateChips").appendChild(chip(`${name} ${count}`, false, null, "gray")));
    }

    function renderLaneCards() {
      const descriptions = {
        "可直接买样": "更接近已经成立的消费品，适合快速买样验证。",
        "适合改造": "方向成立，但更值得拿来二次设计或换结构做法。",
        "方向参考": "更偏趋势、语言和方向，不建议直接推进。"
      };
      const order = ["可直接买样", "适合改造", "方向参考"];
      $("laneCards").innerHTML = order.map(name => `
        <button class="lane-card ${cardClass(name)}" type="button" data-lane="${name}">
          <strong>${name}</strong>
          <em>${payload.stats.by_lane[name] || 0}</em>
          <p>${descriptions[name]}</p>
        </button>
      `).join("");
      Array.from(document.querySelectorAll(".lane-card")).forEach(el => {
        el.addEventListener("click", () => {
          state.lane = el.dataset.lane;
          renderFilters();
          renderMain();
        });
      });
    }

    function renderTrendList() {
      const trends = payload.trends || {};
      const list = [];
      (trends.recommended_directions || []).slice(0, 4).forEach(item => list.push([item, "方向"]));
      (trends.hot_signals || []).slice(0, 3).forEach(item => list.push([item, "信号"]));
      const fallback = Object.entries(payload.stats.by_category).slice(0, 6).map(([name, count]) => `${name} · ${count}`);
      if (!list.length) {
        $("trendList").innerHTML = fallback.map(text => `<div class="trend-item"><strong>${text}</strong><span>当前可见池子里相对更密集的品类。</span></div>`).join("");
        return;
      }
      $("trendList").innerHTML = list.map(([text, label]) => `<div class="trend-item"><strong>${label} · ${text}</strong></div>`).join("");
    }

    function renderQueue() {
      const weekly = payload.weekly_report && payload.weekly_report.recommendations;
      const queue = state.lane === "全部" && weekly && weekly.length
        ? weekly
        : payload.featured.lanes[state.lane === "全部" ? "可直接买样" : state.lane] || [];
      $("queueList").innerHTML = queue.slice(0, 5).map(item => `
        <div class="queue-item">
          <strong>${item.title}</strong>
          <span>${item.action_lane} · ${item.category} · ${item.source_name || item.source}</span>
        </div>
      `).join("");
    }

    function renderFilters() {
      const filters = [
        ["laneFilters", "lane", ["全部", ...Object.keys(payload.stats.by_lane)]],
        ["axisFilters", "axis", ["全部", ...Object.keys(payload.stats.by_axis)]],
        ["categoryFilters", "category", ["全部", ...Object.keys(payload.stats.by_category)]],
        ["sourceFilters", "source", ["全部", ...Object.keys(payload.stats.by_source_family)]]
      ];
      filters.forEach(([id, key, options]) => {
        const root = $(id);
        root.innerHTML = "";
        options.forEach(option => root.appendChild(chip(option, state[key] === option, () => {
          state[key] = option;
          renderFilters();
          renderMain();
        })));
      });
    }

    function match(item) {
      if (state.lane !== "全部" && item.action_lane !== state.lane) return false;
      if (state.axis !== "全部" && !item.axes.includes(state.axis)) return false;
      if (state.category !== "全部" && item.category !== state.category) return false;
      if (state.source !== "全部" && item.source_family !== state.source) return false;
      if (state.q) {
        const text = [
          item.title, item.category, item.summary, item.source_name,
          item.action_lane, item.source_family, ...item.axes, ...(item.tags || [])
        ].join(" ").toLowerCase();
        if (!text.includes(state.q.toLowerCase())) return false;
      }
      return true;
    }

    function priceText(value) {
      if (value === "likely_over_35") return ">35";
      if (value === "risk_under_35") return "低价风险";
      return "价格未知";
    }

    function renderCards() {
      const items = payload.items.filter(match);
      $("emptyState").hidden = items.length > 0;
      $("cardGrid").innerHTML = items.map(item => `
        <article class="card">
          ${item.image ? `<img class="thumb" src="${item.image}" alt="" loading="lazy">` : `<div class="thumb"></div>`}
          <div class="body">
            <div class="meta">
              <span class="pill">${item.action_lane}</span>
              <span class="pill sage">${item.category}</span>
              <span class="pill sky">${priceText(item.price_gate)}</span>
              <span class="pill gray">${item.image_state}</span>
            </div>
            <h2 class="title"><a href="${item.url}" target="_blank" rel="noopener">${item.title}</a></h2>
            <p class="summary">${item.summary || item.review_reason || ""}</p>
            <div class="scoreline">
              <div class="score">${(item.score / 10).toFixed(1)}</div>
              <div class="source">${item.source_name}<br>${item.source_family}</div>
            </div>
            <div class="tags">
              ${item.axes.map(axis => `<span class="pill gray">${axis}</span>`).join("")}
              ${(item.tags || []).slice(0, 3).map(tag => `<span class="pill gray">${tag}</span>`).join("")}
            </div>
          </div>
        </article>
      `).join("");
    }

    function renderMain() {
      renderQueue();
      renderCards();
    }

    $("search").addEventListener("input", event => {
      state.q = event.target.value.trim();
      renderCards();
    });

    renderHero();
    renderLaneCards();
    renderTrendList();
    renderFilters();
    renderMain();
  </script>
</body>
</html>
"""


def main():
    ensure_dirs()
    products = load_json(DATA_DIR / "products.json", [])
    trends = load_json(DATA_DIR / "trends.json", {})
    weekly_report = load_json(DATA_DIR / "weekly_report.json", {})
    payload = build_payload(products, trends, weekly_report)
    write_json(DATA_DIR / "published.json", payload)
    write_json(INSIGHT_DIR / "data.raw.json", payload)
    data_js = "window.__INSIGHT_DATA__ = " + json.dumps(payload, ensure_ascii=False) + ";\n"
    (INSIGHT_DIR / "data.json").write_text(data_js, encoding="utf-8")
    (INSIGHT_DIR / "index.html").write_text(HTML, encoding="utf-8")
    print(f"built insight/index.html items={len(products)}")


if __name__ == "__main__":
    main()
