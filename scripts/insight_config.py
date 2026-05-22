#!/usr/bin/env python3
"""Shared configuration for the Design Daily insight pool."""

CATEGORIES = [
    "水杯",
    "氛围灯",
    "创意礼盒",
    "装置艺术",
    "创意厨具",
    "中秋礼盒",
    "帽子",
    "创意桌搭",
    "端午礼盒",
    "充电宝",
    "日历",
    "T恤",
    "卫衣",
    "卡包",
    "手机壳",
    "收纳包",
    "Polo衫",
    "冲锋衣",
    "钥匙扣水壶",
]

SOURCE_TYPES = {
    "小红书": "social_signal",
    "抖音": "social_signal",
    "Instagram": "social_signal",
    "Pinterest": "social_signal",
    "Behance": "social_signal",
    "Dezeen": "editorial_source",
    "Design Milk": "editorial_source",
    "Yanko Design": "editorial_source",
    "Good Design Award": "verified_official",
    "iF设计奖": "verified_official",
    "Red Dot": "verified_official",
    "A' Design Award": "verified_official",
}

SELECTION_WEIGHTS = {
    "utility": 0.24,
    "frequency": 0.20,
    "broad_appeal": 0.18,
    "functionality": 0.16,
    "price_power": 0.10,
    "clarity": 0.08,
    "emotion": 0.04,
}

SCORING_PRINCIPLES = [
    "实用为先",
    "高频需求",
    "打击面广",
    "产品功能没有明显短板",
    "预估售价大于 35 RMB",
    "3 秒看懂",
    "功能成立后再叠加情绪价值",
]

RSS_FEEDS = [
    {
        "source": "Dezeen",
        "url": "https://www.dezeen.com/feed/",
    },
    {
        "source": "Design Milk",
        "url": "https://design-milk.com/feed/",
    },
    {
        "source": "Yanko Design",
        "url": "https://www.yankodesign.com/feed/",
    },
]

CATEGORY_KEYWORDS = {
    "水杯": ["cup", "mug", "bottle", "tumbler", "flask", "drinkware", "水杯", "杯", "水壶", "保温"],
    "氛围灯": ["lamp", "lighting", "light", "lantern", "chandelier", "灯", "照明", "台灯", "吊灯"],
    "创意礼盒": ["gift", "box", "packaging", "set", "kit", "礼盒", "包装", "礼品", "套装"],
    "装置艺术": ["installation", "sculpture", "public art", "immersive", "装置", "雕塑", "艺术"],
    "创意厨具": ["kitchen", "cookware", "knife", "utensil", "pan", "pot", "厨具", "厨房", "锅", "刀"],
    "中秋礼盒": ["mooncake", "mid autumn", "mid-autumn", "中秋", "月饼"],
    "帽子": ["hat", "cap", "headwear", "beanie", "帽子", "棒球帽", "渔夫帽"],
    "创意桌搭": ["desk", "keyboard", "monitor", "mouse", "cable", "桌面", "桌搭", "键盘", "显示器"],
    "端午礼盒": ["zongzi", "dragon boat", "端午", "粽子"],
    "充电宝": ["power bank", "portable charger", "battery pack", "charger", "充电宝", "移动电源"],
    "日历": ["calendar", "planner", "日历", "台历", "年历"],
    "T恤": ["t-shirt", "tee", "tshirt", "短袖", "t恤"],
    "卫衣": ["hoodie", "sweatshirt", "pullover", "卫衣", "帽衫"],
    "卡包": ["wallet", "card holder", "card case", "卡包", "钱包", "卡夹"],
    "手机壳": ["phone case", "phone cover", "iphone case", "手机壳", "保护壳"],
    "收纳包": ["bag", "pouch", "organizer", "storage", "backpack", "收纳", "包", "背包"],
    "Polo衫": ["polo shirt", "polo衫", "polo"],
    "冲锋衣": ["jacket", "windbreaker", "shell", "parka", "冲锋衣", "夹克", "防风"],
    "钥匙扣水壶": ["keychain", "key ring", "carabiner", "钥匙扣", "钥匙链"],
}

SOCIAL_SEARCH_TEMPLATES = {
    "xiaohongshu": "https://www.xiaohongshu.com/search_result?keyword={query}",
    "douyin": "https://www.douyin.com/search/{query}",
}
