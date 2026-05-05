#!/usr/bin/env python3
"""
Design Daily — 设计灵感数据库生成器
====================================
从 brand_pool.json 加载真实数据，输出到 data.js + data/latest.json
所有数据均为真实品牌/设计项目，支持全部展示或每日轮换展示。

用法:
  python3 generate.py              # 展示全部数据
  python3 generate.py --daily      # 每日随机抽取 30-50 条
  python3 generate.py --count N    # 展示 N 条随机数据
"""
import json, os, sys, random, datetime
from collections import Counter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
POOL_PATH = os.path.join(BASE_DIR, "brand_pool.json")

CATEGORIES = [
    "水杯", "氛围灯", "创意礼盒", "装置艺术", "创意厨具",
    "中秋礼盒", "帽子", "创意桌搭", "端午礼盒", "充电宝",
    "日历", "T恤", "卫衣", "卡包", "手机壳", "收纳包",
    "Polo衫", "冲锋衣", "钥匙扣水壶",
    "生活杂货", "运动户外", "科技数码", "健康美妆",
    "文创文具", "母婴亲子", "时尚配饰",
]


def load_pool():
    """载入品牌数据池"""
    with open(POOL_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def pick_daily(items, seed=None, target_min=35, target_max=50):
    """
    每日按品类均衡抽取。
    - 每个品类至少抽 1-3 条
    - 按日期种子决定随机顺序
    - 总共 target_min ~ target_max 条
    """
    if seed is None:
        seed = datetime.date.today().isoformat()
    rng = random.Random(seed)
    target = target_min + (hash(seed) % (target_max - target_min + 1))

    by_cat = {}
    for item in items:
        cat = item.get("category", "其他")
        by_cat.setdefault(cat, []).append(item)

    # 每品类打乱
    for cat in by_cat:
        rng.shuffle(by_cat[cat])

    selected = []
    used_titles = set()

    # 第1轮：各品类抽 1 条保底
    for cat in CATEGORIES:
        pool_cat = by_cat.get(cat, [])
        for item in pool_cat:
            if item["title"] not in used_titles:
                selected.append(item)
                used_titles.add(item["title"])
                break

    # 第2轮：数据多的品类多抽
    for cat in CATEGORIES:
        pool_cat = by_cat.get(cat, [])
        extra = min(3, len(pool_cat))
        count = 0
        for item in pool_cat:
            if count >= extra or len(selected) >= target:
                break
            if item["title"] in used_titles:
                continue
            selected.append(item)
            used_titles.add(item["title"])
            count += 1

    # 第3轮：从冷门品类补
    if len(selected) < target:
        remaining = [i for i in items if i["title"] not in used_titles]
        rng.shuffle(remaining)
        for item in remaining:
            if len(selected) >= target:
                break
            selected.append(item)
            used_titles.add(item["title"])

    rng.shuffle(selected)
    return selected


def write_output(items, show_all=True):
    """写入 data.js 和 data/latest.json"""
    src_counter = Counter(i["source"] for i in items)
    cat_counter = Counter(i["category"] for i in items)

    os.makedirs(DATA_DIR, exist_ok=True)

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

    # data.js（前端加载用）
    js_path = os.path.join(BASE_DIR, "data.js")
    with open(js_path, "w", encoding="utf-8") as f:
        js = json.dumps(result, ensure_ascii=False)
        f.write(f"const digestData = {js};")

    # latest.json
    json_path = os.path.join(DATA_DIR, "latest.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # 统计
    mode = "全部展示" if show_all else "每日抽取"
    print(f"\n✅ {mode} · {len(items)} 条")
    print(f"   📁 {js_path}")
    print(f"   📁 {json_path}")
    print(f"   来源: {', '.join(f'{s}:{n}' for s, n in src_counter.most_common())}")
    print(f"   品类: {len(cat_counter)} 个品类全覆盖" if len(cat_counter) >= 19 else f"   品类: {len(cat_counter)} 个 (请检查品类覆盖率)")


def main():
    pool = load_pool()
    print(f"📦 品牌池: {len(pool)} 条")
    print(f"   来源: {len(Counter(i['source'] for i in pool))} 个")
    print(f"   品类: {len(Counter(i['category'] for i in pool))} 个")

    # 确定模式
    show_all = True
    if "--daily" in sys.argv:
        show_all = False
        seed = datetime.date.today().isoformat()
        target = 35 + (hash(seed) % 16)
        print(f"\n📋 每日模式 · 种子={seed} · 目标={target} 条")
        items = pick_daily(pool, seed)
        write_output(items, show_all=False)

    elif any(a.startswith("--count=") for a in sys.argv):
        show_all = False
        count = int([a for a in sys.argv if a.startswith("--count=")][0].split("=")[1])
        seed = datetime.date.today().isoformat()
        rng = random.Random(seed)
        items = sorted(pool, key=lambda x: rng.random())[:count]
        print(f"\n📋 随机抽取 {count} 条")
        write_output(items, show_all=False)

    else:
        # 默认：展示全部数据
        print(f"\n📋 全量模式 · 展示全部 {len(pool)} 条")
        write_output(pool, show_all=True)


if __name__ == "__main__":
    main()
