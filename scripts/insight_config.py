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

CATEGORY_REVIEW_RULES = {
    "水杯": "Only drinkware: cups, mugs, bottles, tumblers, flasks, thermos products, and clearly related drink containers.",
    "氛围灯": "Only lighting products for ambience or daily use: table lamps, night lights, decorative lamps, lanterns, light fixtures.",
    "创意礼盒": "Only gift boxes, gift sets, creative packaging sets, boxed gift products, and reusable gift packaging.",
    "装置艺术": "Only purchasable or inspiration-worthy installation art objects, public art, sculptural installations, or immersive art pieces.",
    "创意厨具": "Only kitchen tools, cookware, cooking utensils, food preparation tools, tableware tools, or kitchen appliances.",
    "中秋礼盒": "Only Mid-Autumn Festival gift boxes, mooncake packaging, mooncake sets, or clearly Mid-Autumn themed gifts.",
    "帽子": "Only hats and headwear: caps, beanies, bucket hats, helmets only when clearly sold as fashion/headwear rather than sports gear.",
    "创意桌搭": "Only desk setup products: desk accessories, monitor/keyboard/mouse accessories, cable management, desktop storage, work desk objects.",
    "端午礼盒": "Only Dragon Boat Festival gift boxes, zongzi packaging, zongzi sets, or clearly Dragon Boat themed gifts.",
    "充电宝": "Only power banks, portable chargers, battery packs, and portable power stations.",
    "日历": "Only calendars, planners, desktop calendars, wall calendars, and calendar-like date display products.",
    "T恤": "Only T-shirts and short-sleeve tee apparel.",
    "卫衣": "Only hoodies, sweatshirts, pullovers, and sweatshirt-like apparel.",
    "卡包": "Only card holders, slim wallets, card cases, passport/card organizers, and small card storage goods.",
    "手机壳": "Only phone cases, phone covers, phone protection shells, and direct phone case accessories.",
    "收纳包": "Only storage bags, organizer pouches, daily carry pouches, travel organizers, packing bags, and product cases meant mainly for storage.",
    "Polo衫": "Only polo shirts.",
    "冲锋衣": "Only outdoor jackets, shell jackets, windbreakers, rain jackets, sun-protection jackets, and functional outerwear. Reject shoes, gloves, tents, binoculars, sports balls, general outdoor gear, pet products, and unrelated sports equipment.",
    "钥匙扣水壶": "Only keychains, key rings, small hanging accessories, mini bottles attached to keychains, carabiner-like key accessories, or clearly keychain bottle products.",
}

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

SEARCH_INTENTS = {
    "buy_sample": "更接近现成消费品，适合买样验证",
    "adapt": "适合做结构、包装、功能或外观改造",
    "trend": "适合作为趋势、内容爆点或方向参考",
}

SEARCH_QUERY_PATTERNS = {
    "水杯": ["new water bottle design", "creative tumbler", "便携 水杯 新品", "保温杯 创意 设计"],
    "氛围灯": ["cute night light", "ambient table lamp", "氛围灯 礼物", "小夜灯 创意"],
    "创意礼盒": ["creative gift box packaging", "gift set packaging idea", "创意礼盒 包装", "礼盒 设计 灵感"],
    "装置艺术": ["small installation art object", "interactive light installation", "装置艺术 商业 空间", "光影装置 灵感"],
    "创意厨具": ["new kitchen gadget", "creative kitchen tool", "厨房神器 新品", "创意厨具"],
    "中秋礼盒": ["mooncake gift box packaging", "mid autumn gift set design", "中秋礼盒 包装", "月饼礼盒 创意"],
    "帽子": ["creative cap design", "cute hat trend", "帽子 创意 设计", "棒球帽 新品"],
    "创意桌搭": ["desk organizer design", "creative desk accessory", "桌搭 收纳 新品", "桌面好物 创意"],
    "端午礼盒": ["dragon boat festival gift box", "zongzi packaging design", "端午礼盒 包装", "粽子礼盒 创意"],
    "充电宝": ["portable power bank design", "cute power bank", "充电宝 创意", "移动电源 新品"],
    "日历": ["creative calendar design", "desk calendar product", "日历 创意", "台历 设计"],
    "T恤": ["graphic t shirt trend", "creative tee design", "T恤 图案 趋势", "短袖 创意"],
    "卫衣": ["hoodie design trend", "creative sweatshirt", "卫衣 图案 趋势", "连帽卫衣 创意"],
    "卡包": ["card holder design", "slim wallet product", "卡包 创意", "卡夹 新品"],
    "手机壳": ["phone case trend", "creative iphone case", "手机壳 创意", "手机壳 爆款"],
    "收纳包": ["organizer pouch design", "travel storage bag", "收纳包 创意", "便携收纳 新品"],
    "Polo衫": ["polo shirt design trend", "creative polo shirt", "Polo衫 设计", "Polo衫 新品"],
    "冲锋衣": ["lightweight shell jacket trend", "packable rain jacket", "冲锋衣 新品", "防晒衣 创意"],
    "钥匙扣水壶": ["keychain bottle", "creative keychain accessory", "钥匙扣 水壶", "钥匙扣 创意"],
}

SEARCH_SOURCE_GROUPS = {
    "global_web": [
        "site:trendhunter.com",
        "site:kickstarter.com",
        "site:indiegogo.com",
        "site:producthunt.com",
        "site:designboom.com",
        "site:core77.com",
        "site:thegadgetflow.com",
    ],
    "brand_and_shop": [
        "site:amazon.com",
        "site:etsy.com",
        "site:uncommongoods.com",
        "site:urbanoutfitters.com",
        "site:muji.com",
    ],
    "china_reference": [
        "site:smzdm.com",
        "site:1688.com",
        "site:taobao.com",
    ],
}
