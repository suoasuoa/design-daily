#!/usr/bin/env python3
"""Shared configuration for the Design Daily insight pool."""

RETIRED_CATEGORY_CUTOFF = "2026-07-16"
DAILY_TARGET_40_CUTOFF = "2026-07-20"
LEGACY_DAILY_TARGET = 30
RETIRED_CATEGORIES = {
    "T恤",
    "帽子",
    "卫衣",
    "Polo衫",
    "收纳包",
    "卡包",
}

CATEGORIES = [
    "水杯",
    "氛围灯",
    "创意礼盒",
    "装置艺术",
    "创意厨具",
    "中秋礼盒",
    "创意桌搭",
    "端午礼盒",
    "充电宝",
    "日历",
    "手机壳",
    "冲锋衣",
    "钥匙扣水壶",
]

CATEGORY_REVIEW_RULES = {
    "水杯": "必须是可直接饮用的杯、瓶、随行杯、保温杯、酒壶或水壶。排除电热水壶、咖啡机、茶具套装、花瓶、普通餐具和仅含 cup/bottle 字样的文章。必须有结构、便携、清洁、保温、交互或材料创新，普通基础杯不收。",
    "氛围灯": "必须是明确的可使用灯具单品，如台灯、夜灯、提灯、壁灯或吊灯。排除建筑照明新闻、展览报道、纯灯光装置、常规灯具和只有造型变化却无使用价值的作品。",
    "创意礼盒": "必须是明确礼盒或礼赠包装，且有结构、开箱、复用、材料或叙事创新。排除普通套装、玩具/模型/商品组合、仅做平面换肤的盒子以及没有展示包装设计的品牌新闻。",
    "装置艺术": "必须是边界清楚的互动、光影、机械、材料或雕塑装置，并能提炼成产品启发。排除建筑、室内空间、汽车、活动新闻、纯公共工程和无法转化的宏大概念。",
    "创意厨具": "必须直接用于烹饪、备餐、盛取、清洁或厨房操作。排除纸扇、摆件、普通餐盘、家居装饰及仅因材料好看而没有功能创新的基础厨具。",
    "中秋礼盒": "必须是明确的中秋/月饼礼盒，并具有包装结构、开箱、复用、材料或节日叙事创新。排除普通月饼盒、仅换插画或品牌联名贴图的产品。",
    "创意桌搭": "必须直接服务桌面工作、整理、输入、显示、充电或收纳。排除普通文具、手电筒、传统通讯录、泛家居摆件及无法说明桌面价值的产品。",
    "端午礼盒": "必须是明确的端午/粽子礼盒，并具有包装结构、开箱、复用、材料或节日叙事创新。排除普通粽子盒、仅换插画或品牌联名贴图的产品。",
    "充电宝": "必须是面向日常携带的充电宝、移动电源或便携电池产品。排除充电线、墙充、普通插座、大型户外电站及没有便携产品创新的基础款。",
    "日历": "必须以日期展示或日程规划为核心，并有机械、交互、内容、材料或可持续创新。排除普通台历、过期年份基础日历、纯记事本和只有印刷图案变化的产品。",
    "手机壳": "必须是直接安装在手机上的保护壳/外壳，并有结构、功能、材料或交互创新。排除 AirTag 配件、手机包、支架、挂绳、普通皮壳、普通印花壳及泛 case 产品。",
    "冲锋衣": "必须是可穿着的功能外套，如硬壳、软壳、防风、防雨或防晒夹克，并有材料、结构、收纳、透气或场景创新。排除鞋、手套、帐篷、望远镜、球类、包具和其他户外装备，也排除普通品牌基础款。",
    "钥匙扣水壶": "必须是把饮水容器与钥匙扣、挂环或迷你随身结构真正结合的产品。排除普通钥匙扣、AirTag 套、登山扣、多功能工具、挂件和不具备饮水容器功能的饰品。",
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
    "Core77": "editorial_source",
    "Designboom": "editorial_source",
    "DesignWanted": "editorial_source",
    "NOTCOT": "editorial_source",
    "Wallpaper": "editorial_source",
    "TrendHunter": "trend_source",
    "The Dieline": "packaging_source",
    "Packaging of the World": "packaging_source",
    "Pentawards": "packaging_source",
    "BP&O": "packaging_source",
    "Lovely Package": "packaging_source",
    "Good Design Award": "verified_official",
    "iF设计奖": "verified_official",
    "Red Dot": "verified_official",
    "DIA 中国设计智造大奖": "verified_official",
    "A' Design Award": "verified_official",
    "IDEA": "verified_official",
    "站酷": "design_community",
    "普象网": "design_community",
    "设计癖": "design_community",
    "数英": "design_community",
    "Threadless": "market_reference",
    "Kickstarter": "market_reference",
    "Indiegogo": "market_reference",
    "Product Hunt": "market_reference",
    "Uncrate": "market_reference",
    "Uncrate Shop": "market_reference",
    "Cool Material": "market_reference",
    "Gear Patrol": "market_reference",
    "ThisIsWhyImBroke": "market_reference",
    "The Grommet": "market_reference",
    "Etsy": "market_reference",
}

SOURCE_QUALITY_BY_SOURCE = {
    "Good Design Award": "premium",
    "iF设计奖": "premium",
    "Red Dot": "premium",
    "DIA 中国设计智造大奖": "premium",
    "A' Design Award": "premium",
    "IDEA": "premium",
    "Dezeen": "premium",
    "Design Milk": "premium",
    "Yanko Design": "premium",
    "Core77": "premium",
    "Designboom": "premium",
    "DesignWanted": "premium",
    "NOTCOT": "premium",
    "Wallpaper": "premium",
    "The Dieline": "premium",
    "Packaging of the World": "premium",
    "Pentawards": "premium",
    "BP&O": "premium",
    "Lovely Package": "premium",
    "Uncrate": "premium",
    "Uncrate Shop": "premium",
    "Kickstarter": "standard",
    "Indiegogo": "standard",
    "Cool Material": "standard",
    "Gear Patrol": "standard",
    "The Grommet": "standard",
    "站酷": "standard",
    "普象网": "standard",
    "设计癖": "standard",
    "数英": "standard",
    "Behance": "standard",
    "Pinterest": "standard",
    "TrendHunter": "weak",
    "Product Hunt": "weak",
    "Threadless": "weak",
    "ThisIsWhyImBroke": "weak",
    "Etsy": "weak",
}

SOURCE_DOMAIN_META = {
    "dezeen.com": {"source": "Dezeen", "source_type": "editorial_source"},
    "design-milk.com": {"source": "Design Milk", "source_type": "editorial_source"},
    "yankodesign.com": {"source": "Yanko Design", "source_type": "editorial_source"},
    "core77.com": {"source": "Core77", "source_type": "editorial_source"},
    "designboom.com": {"source": "Designboom", "source_type": "editorial_source"},
    "designwanted.com": {"source": "DesignWanted", "source_type": "editorial_source"},
    "notcot.org": {"source": "NOTCOT", "source_type": "editorial_source"},
    "wallpaper.com": {"source": "Wallpaper", "source_type": "editorial_source"},
    "trendhunter.com": {"source": "TrendHunter", "source_type": "trend_source"},
    "thedieline.com": {"source": "The Dieline", "source_type": "packaging_source"},
    "packagingoftheworld.com": {"source": "Packaging of the World", "source_type": "packaging_source"},
    "pentawards.com": {"source": "Pentawards", "source_type": "packaging_source"},
    "bpando.org": {"source": "BP&O", "source_type": "packaging_source"},
    "lovelypackage.com": {"source": "Lovely Package", "source_type": "packaging_source"},
    "red-dot.org": {"source": "Red Dot", "source_type": "verified_official"},
    "ifdesign.com": {"source": "iF设计奖", "source_type": "verified_official"},
    "g-mark.org": {"source": "Good Design Award", "source_type": "verified_official"},
    "di-award.org": {"source": "DIA 中国设计智造大奖", "source_type": "verified_official"},
    "idsa.org": {"source": "IDEA", "source_type": "verified_official"},
    "zcool.com.cn": {"source": "站酷", "source_type": "design_community"},
    "puxiang.com": {"source": "普象网", "source_type": "design_community"},
    "shejipi.com": {"source": "设计癖", "source_type": "design_community"},
    "digitaling.com": {"source": "数英", "source_type": "design_community"},
    "behance.net": {"source": "Behance", "source_type": "social_signal"},
    "threadless.com": {"source": "Threadless", "source_type": "market_reference"},
    "kickstarter.com": {"source": "Kickstarter", "source_type": "market_reference"},
    "indiegogo.com": {"source": "Indiegogo", "source_type": "market_reference"},
    "producthunt.com": {"source": "Product Hunt", "source_type": "market_reference"},
    "uncrate.com": {"source": "Uncrate", "source_type": "market_reference"},
    "shop.uncrate.com": {"source": "Uncrate Shop", "source_type": "market_reference"},
    "coolmaterial.com": {"source": "Cool Material", "source_type": "market_reference"},
    "gearpatrol.com": {"source": "Gear Patrol", "source_type": "market_reference"},
    "thisiswhyimbroke.com": {"source": "ThisIsWhyImBroke", "source_type": "market_reference"},
    "thegrommet.com": {"source": "The Grommet", "source_type": "market_reference"},
    "etsy.com": {"source": "Etsy", "source_type": "market_reference"},
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
    {
        "source": "Core77",
        "url": "https://www.core77.com/rss/all.xml",
    },
    {
        "source": "Designboom",
        "url": "https://www.designboom.com/feed/",
    },
    {
        "source": "The Dieline",
        "url": "https://thedieline.com/feed/",
    },
    {
        "source": "Packaging of the World",
        "url": "https://packagingoftheworld.com/feed/",
    },
    {
        "source": "DesignWanted",
        "url": "https://designwanted.com/feed/",
    },
    {
        "source": "Uncrate",
        "url": "https://uncrate.com/feed/",
    },
    {
        "source": "Cool Material",
        "url": "https://coolmaterial.com/gear/feed/",
    },
    {
        "source": "ThisIsWhyImBroke",
        "url": "https://www.thisiswhyimbroke.com/feed/",
    },
    {
        "source": "Product Hunt",
        "url": "https://www.producthunt.com/feed",
    },
]

CATEGORY_KEYWORDS = {
    "水杯": ["cup", "mug", "bottle", "tumbler", "flask", "drinkware", "水杯", "杯", "水壶", "保温"],
    "氛围灯": ["lamp", "lighting", "light", "lantern", "chandelier", "灯", "照明", "台灯", "吊灯"],
    "创意礼盒": ["gift", "box", "packaging", "set", "kit", "礼盒", "包装", "礼品", "套装"],
    "装置艺术": ["installation", "sculpture", "public art", "immersive", "装置", "雕塑", "艺术"],
    "创意厨具": ["kitchen", "cookware", "knife", "utensil", "pan", "pot", "厨具", "厨房", "锅", "刀"],
    "中秋礼盒": ["mooncake", "mid autumn", "mid-autumn", "中秋", "月饼"],
    "创意桌搭": ["desk", "keyboard", "monitor", "mouse", "cable", "桌面", "桌搭", "键盘", "显示器"],
    "端午礼盒": ["zongzi", "dragon boat", "端午", "粽子"],
    "充电宝": ["power bank", "portable charger", "battery pack", "charger", "充电宝", "移动电源"],
    "日历": ["calendar", "planner", "日历", "台历", "年历"],
    "手机壳": ["phone case", "phone cover", "iphone case", "手机壳", "保护壳"],
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
    "创意桌搭": ["desk organizer design", "creative desk accessory", "桌搭 收纳 新品", "桌面好物 创意"],
    "端午礼盒": ["dragon boat festival gift box", "zongzi packaging design", "端午礼盒 包装", "粽子礼盒 创意"],
    "充电宝": ["portable power bank design", "cute power bank", "充电宝 创意", "移动电源 新品"],
    "日历": ["creative calendar design", "desk calendar product", "日历 创意", "台历 设计"],
    "手机壳": ["phone case trend", "creative iphone case", "手机壳 创意", "手机壳 爆款"],
    "冲锋衣": ["lightweight shell jacket trend", "packable rain jacket", "冲锋衣 新品", "防晒衣 创意"],
    "钥匙扣水壶": ["keychain bottle", "creative keychain accessory", "钥匙扣 水壶", "钥匙扣 创意"],
}

SEARCH_SOURCE_GROUPS = {
    "editorial_main": [
        "site:dezeen.com/design",
        "site:yankodesign.com",
        "site:design-milk.com",
        "site:core77.com",
        "site:designboom.com/design",
        "site:designwanted.com",
        "site:notcot.org",
        "site:wallpaper.com/design",
    ],
    "award_gallery": [
        "site:red-dot.org/project",
        "site:ifdesign.com/en/winner-ranking/project",
        "site:g-mark.org/en/gallery/winners",
        "site:di-award.org",
        "site:idsa.org/awards",
    ],
    "packaging_specialist": [
        "site:thedieline.com",
        "site:packagingoftheworld.com",
        "site:pentawards.com",
        "site:bpando.org",
        "site:lovelypackage.com",
        "site:zcool.com.cn/work 包装",
        "site:digitaling.com/projects 礼盒",
    ],
    "design_community": [
        "site:zcool.com.cn/work",
        "site:puxiang.com",
        "site:shejipi.com",
        "site:behance.net/gallery",
        "site:digitaling.com/projects",
    ],
    "market_signal_strong": [
        "site:kickstarter.com",
        "site:indiegogo.com",
        "site:uncrate.com",
        "site:coolmaterial.com",
        "site:gearpatrol.com",
        "site:thegrommet.com",
    ],
    "market_signal_weak": [
        "site:trendhunter.com",
        "site:producthunt.com",
        "site:threadless.com",
        "site:thisiswhyimbroke.com",
        "site:etsy.com/listing",
    ],
}

SOURCE_GROUP_QUALITY = {
    "award_gallery": "premium",
    "editorial_main": "premium",
    "packaging_specialist": "premium",
    "design_community": "standard",
    "market_signal_strong": "standard",
    "market_signal_weak": "weak",
    "curated_keyword": "standard",
}

CATEGORY_SOURCE_GROUPS = {
    "创意礼盒": ["packaging_specialist", "design_community", "award_gallery", "editorial_main"],
    "中秋礼盒": ["packaging_specialist", "design_community", "award_gallery"],
    "端午礼盒": ["packaging_specialist", "design_community", "award_gallery"],
    "装置艺术": ["editorial_main", "award_gallery", "design_community", "market_signal_strong"],
    "手机壳": ["award_gallery", "design_community", "market_signal_strong", "market_signal_weak"],
    "充电宝": ["award_gallery", "editorial_main", "market_signal_strong"],
}
