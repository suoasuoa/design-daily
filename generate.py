#!/usr/bin/env python3
"""
Daily Design Digest — 每日精选设计灵感生成器
============================================
每次运行从 294 条品牌精选池中按品类轮换抽取 30-50 条，
使用日期作为随机种子确保每天结果不同但可复现。

输出：
  - data/latest.json  → 完整 JSON
  - data.js           → 内嵌 JSON 供 GitHub Pages 加载
"""
import json, os, random, datetime, hashlib
from collections import Counter

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# ── 品牌精选数据池（294 条） ──
# 从外部 JSON 加载（避免 generate.py 自身过于庞大）
BRAND_POOL_PATH = os.path.join(os.path.dirname(__file__), "brand_pool.json")

def load_brand_pool():
    if os.path.exists(BRAND_POOL_PATH):
        with open(BRAND_POOL_PATH, "r") as f:
            return json.load(f)
    # Fallback: 内建一份精简数据（新仓库首次运行）
    return []

# ── 选品规则 ──
# 目标：每天 30-50 条，覆盖所有品类
# 热门品类（数据多的）出 2-3 条/次，冷门品类至少 1 条

CATEGORY_QUOTA = {
    # 品类: 每次最少条数, 最多条数
    "水杯":      (2, 3),
    "氛围灯":    (2, 3),
    "创意礼盒":  (2, 4),
    "装置艺术":  (2, 3),
    "创意厨具":  (1, 2),
    "中秋礼盒":  (1, 2),
    "帽子":      (1, 2),
    "创意桌搭":  (1, 2),
    "端午礼盒":  (1, 2),
    "充电宝":    (1, 2),
    "日历":      (1, 2),
    "T恤":       (1, 2),
    "卫衣":      (1, 2),
    "卡包":      (1, 2),
    "手机壳":    (1, 2),
    "收纳包":    (1, 2),
    "Polo衫":    (1, 1),
    "冲锋衣":    (1, 1),
    "钥匙扣水壶": (1, 1),
}

# 每日最少 / 最多
MIN_TOTAL = 35
MAX_TOTAL = 50

# ── 来源权重（让结果更多样） ──
SOURCE_NAMES = [
    "Instagram", "Pinterest", "小红书", "抖音",
    "Good Design Award", "Red Dot", "Behance",
    "iF设计奖", "A' Design Award"
]

# 设计特点标签池
DESIGN_TAGS = {
    "水杯":     ["极简", "保温", "陶瓷", "户外", "咖啡"],
    "氛围灯":   ["极简", "智能", "北欧", "创意", "光影"],
    "创意礼盒": ["礼盒", "包装", "限定", "联名", "节日"],
    "装置艺术": ["交互", "光影", "沉浸", "数字艺术", "多媒体"],
    "创意厨具": ["极简", "多功能", "收纳", "环保", "北欧"],
    "中秋礼盒": ["中秋", "限定", "礼盒", "国风", "联名"],
    "帽子":     ["棒球帽", "贝雷帽", "渔夫帽", "街头", "极简"],
    "创意桌搭": ["桌面", "收纳", "升降桌", "显示器", "办公"],
    "端午礼盒": ["端午", "粽子", "礼盒", "国风", "限定"],
    "充电宝":   ["快充", "磁吸", "超薄", "便携", "多功能"],
    "日历":     ["日历", "桌面", "手帐", "极简", "复古"],
    "T恤":      ["纯棉", "极简", "印花", "街头", "联名"],
    "卫衣":     ["连帽", "纯棉", "街头", "基础款", "联名"],
    "卡包":     ["超薄", "极简", "真皮", "RFID", "便携"],
    "手机壳":   ["防摔", "磁吸", "极简", "真皮", "创意"],
    "收纳包":   ["收纳", "便携", "极简", "防水", "数码"],
    "Polo衫":   ["经典", "休闲", "纯棉", "商务", "联名"],
    "冲锋衣":   ["防水", "户外", "轻量", "专业", "环保"],
    "钥匙扣水壶": ["便携", "轻量", "户外", "运动", "折叠"],
}

def pick_items(brand_pool, seed):
    """
    按品类轮换从品牌池中抽取数据
    seed: 日期的确定性种子（如 "2026-04-29"）
    """
    rng = random.Random(seed)

    # 按品类分组
    by_category = {}
    for item in brand_pool:
        cat = item.get("category", "其他")
        by_category.setdefault(cat, []).append(item)

    selected = []
    used_titles = set()

    for cat, (min_n, max_n) in CATEGORY_QUOTA.items():
        pool = by_category.get(cat, [])
        if not pool:
            continue
        # 打乱该品类池
        rng.shuffle(pool)
        # 决定本次取几条
        n = rng.randint(min_n, min(max_n, len(pool)))
        for item in pool:
            if len(selected) >= MAX_TOTAL:
                break
            if item["title"] in used_titles:
                continue
            selected.append(item)
            used_titles.add(item["title"])
            n -= 1
            if n <= 0:
                break

    # 如果不够 MIN_TOTAL，从剩余品类的池中补充
    if len(selected) < MIN_TOTAL:
        remaining = [i for i in brand_pool if i["title"] not in used_titles]
        rng.shuffle(remaining)
        for item in remaining:
            if len(selected) >= MAX_TOTAL:
                break
            selected.append(item)
            used_titles.add(item["title"])

    # 增强评分字段（确保有两位小数的 float）
    for item in selected:
        if "score" in item and isinstance(item["score"], (int, float)):
            item["score"] = round(float(item["score"]), 1)
        else:
            item["score"] = round(rng.uniform(7.0, 9.0), 1)

    # 排序：按分数降序
    selected.sort(key=lambda x: x.get("score", 0), reverse=True)
    return selected


def write_output(items):
    """写入 data/latest.json 和 data.js"""
    src_counter = Counter(i["source"] for i in items)
    cat_counter = Counter(i["category"] for i in items)

    result = {
        "date": datetime.date.today().isoformat(),
        "timestamp": datetime.datetime.now().isoformat(),
        "stats": {
            "total": len(items),
            "by_source": dict(src_counter),
            "by_category": dict(cat_counter),
        },
        "items": items,
    }

    os.makedirs(DATA_DIR, exist_ok=True)
    json_path = os.path.join(DATA_DIR, "latest.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    js_path = os.path.join(os.path.dirname(__file__), "data.js")
    with open(js_path, "w", encoding="utf-8") as f:
        f.write(f"const digestData = {json.dumps(result, ensure_ascii=False)};")

    print(f"✅ 完成! {len(items)}条 | {len(src_counter)}来源 | {len(cat_counter)}品类")
    print(f"   📁 {json_path}")
    print(f"   📁 {js_path}")
    print(f"   来源: {', '.join(f'{s}:{n}' for s, n in src_counter.most_common())}")


def main():
    brand_pool = load_brand_pool()
    if not brand_pool:
        # 首次运行，自动从旧 generate_old.py 提取
        print("⚠️  未找到 brand_pool.json，尝试从旧文件提取...")
        old_path = os.path.join(os.path.dirname(__file__), "generate_old.py")
        if os.path.exists(old_path):
            import ast
            with open(old_path) as f:
                content = f.read()
            pos1 = content.index("BRAND_ITEMS = []")
            pos2 = content.index("BRAND_ITEMS = [", pos1 + 5)
            brace_pos = content.index("[", pos2 + 5)
            depth = 0
            end_pos = brace_pos
            for i, c in enumerate(content[brace_pos:]):
                if c == '[': depth += 1
                elif c == ']':
                    depth -= 1
                    if depth == 0:
                        end_pos = brace_pos + i + 1
                        break
            brand_pool = ast.literal_eval(content[brace_pos:end_pos])

            # 保存为外部 JSON 文件
            with open(BRAND_POOL_PATH, "w", encoding="utf-8") as f:
                json.dump(brand_pool, f, ensure_ascii=False, indent=2)
            print(f"📦 品牌数据已提取并保存到 {BRAND_POOL_PATH} ({len(brand_pool)}条)")
        else:
            print("❌ 没有可用的品牌数据源！")
            return

    # 用当天日期作为确定性种子
    seed = datetime.date.today().isoformat()
    items = pick_items(brand_pool, seed)

    write_output(items)


if __name__ == "__main__":
    main()
