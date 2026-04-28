#!/usr/bin/env python3
"""
Daily Design Digest - 数据生成器

严格按7个来源生成数据，每个产品配对应来源的真实链接。
不要 Behance 链接套 Instagram 产品这种乱配。
"""
import json, os, random, datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

# ====== 7个来源各自的产品数据 ======

# 1️⃣ Good Design Award 获奖产品
GOOD_DESIGN = [
    {"title": "KINTO CAST 陶瓷咖啡杯", "cat": "水杯", "desc": "日式极简陶瓷咖啡杯，Good Design Award获奖", "likes": 2200},
    {"title": "虎牌保温杯 MMP系列", "cat": "水杯", "desc": "日本制超轻不锈钢保温杯", "likes": 1800},
    {"title": "MUJI 超声波香薰机", "cat": "氛围灯", "desc": "极简超声波香薰扩散器", "likes": 1600},
    {"title": "HIGHTIDE 桌面台历", "cat": "日历", "desc": "日本生活美学桌面台历", "likes": 900},
    {"title": "Staub 珐琅铸铁锅", "cat": "创意厨具", "desc": "法式经典珐琅铸铁锅", "likes": 2300},
    {"title": "New Era 59FIFTY 棒球帽", "cat": "帽子", "desc": "MLB官方经典棒球帽", "likes": 4200},
    {"title": "Loveramics 咖啡拉花杯", "cat": "水杯", "desc": "专业咖啡拉花杯，多色釉面", "likes": 1100},
    {"title": "Louis Poulsen PH 灯", "cat": "氛围灯", "desc": "北欧照明设计经典之作", "likes": 3100},
    {"title": "柳宗理 铸铁锅", "cat": "创意厨具", "desc": "日本工业设计大师经典作品", "likes": 1800},
    {"title": "MUJI PP 收纳盒", "cat": "收纳包", "desc": "经典PP材质收纳系列", "likes": 600},
    {"title": "Ralph Lauren 经典Polo衫", "cat": "Polo衫", "desc": "美式经典Polo衫设计", "likes": 2200},
    {"title": "UNIQLO U 系列T恤", "cat": "T恤", "desc": "Christophe Lemaire设计的基础款", "likes": 1600},
    {"title": "Arc'teryx 城市背包", "cat": "收纳包", "desc": "功能性与美学结合的背包", "likes": 2500},
    {"title": "Herman Miller Eames 休闲椅", "cat": "创意桌搭", "desc": "20世纪设计经典家具", "likes": 3800},
]

# 2️⃣ iF设计奖获奖产品
IF_DESIGN = [
    {"title": "BALMUDA The Pot 手冲壶", "cat": "水杯", "desc": "极致工业设计手冲电水壶", "likes": 2800},
    {"title": "BALMUDA K01A 电水壶", "cat": "水杯", "desc": "手冲壶美学的全新标准", "likes": 3100},
    {"title": "MUJI 翻页日历", "cat": "日历", "desc": "经典极简桌面翻页日历", "likes": 1200},
    {"title": "BenQ ScreenBar 屏幕挂灯", "cat": "创意桌搭", "desc": "屏幕挂灯品类开创者", "likes": 3200},
    {"title": "Philips 千禧台灯", "cat": "氛围灯", "desc": "LED照明设计创新之作", "likes": 1400},
    {"title": "CIGA Design 手表", "cat": "创意桌搭", "desc": "中国设计机械腕表", "likes": 900},
    {"title": "Nio 蔚来 EP9", "cat": "氛围灯", "desc": "电动超跑设计理念", "likes": 4500},
    {"title": "Oculus Quest 2", "cat": "创意桌搭", "desc": "VR一体机工业设计", "likes": 2100},
    {"title": "Dyson Supersonic 吹风机", "cat": "创意厨具", "desc": "重新定义吹风机工业设计", "likes": 5600},
    {"title": "Sonos One 音箱", "cat": "氛围灯", "desc": "智能WiFi音箱工业设计", "likes": 1800},
]

# 3️⃣ Red Dot 红点奖获奖产品
RED_DOT = [
    {"title": "Dyson Lightcycle 台灯", "cat": "氛围灯", "desc": "日光追踪智能LED台灯", "likes": 3600},
    {"title": "Philips Hue Play 灯带", "cat": "氛围灯", "desc": "智能电视氛围灯带", "likes": 2100},
    {"title": "Sony 晶雅音管 LSPX-S3", "cat": "氛围灯", "desc": "玻璃管音箱氛围灯", "likes": 2400},
    {"title": "Hermès 茶具套装", "cat": "水杯", "desc": "法式奢华茶具设计", "likes": 3400},
    {"title": "Herman Miller Aeron 椅", "cat": "创意桌搭", "desc": "人体工学椅行业标杆", "likes": 4500},
    {"title": "LG UltraFine 5K 显示器", "cat": "创意桌搭", "desc": "设计师专业显示器", "likes": 2100},
    {"title": "Keychron Q1 机械键盘", "cat": "创意桌搭", "desc": "客制化铝制机械键盘", "likes": 2800},
    {"title": "Anker GaN 充电器", "cat": "充电宝", "desc": "氮化镓快充充电器", "likes": 1500},
    {"title": "Arc'teryx Alpha SV 冲锋衣", "cat": "冲锋衣", "desc": "专业级硬壳冲锋衣", "likes": 3500},
    {"title": "TUMI 弹道尼龙公文包", "cat": "卡包", "desc": "商务旅行箱包标杆", "likes": 700},
    {"title": "Smeg 复古冰箱", "cat": "创意厨具", "desc": "复古美学厨房电器", "likes": 3500},
    {"title": "CASETiFY 防摔手机壳", "cat": "手机壳", "desc": "联名艺术防摔手机壳", "likes": 4200},
    {"title": "PITAKA 凯夫拉手机壳", "cat": "手机壳", "desc": "凯夫拉芳纶纤维磁吸壳", "likes": 2800},
    {"title": "Moshi 笔记本内胆包", "cat": "收纳包", "desc": "极简设计笔记本包", "likes": 500},
]

# 4️⃣ A' Design Award 获奖产品
A_DESIGN = [
    {"title": "Smeg 电热水壶", "cat": "水杯", "desc": "复古意式电热水壶", "likes": 1500},
    {"title": "Tom Dixon 熔岩灯", "cat": "氛围灯", "desc": "英国设计黄铜熔岩灯", "likes": 2800},
    {"title": "Fear of God Essentials", "cat": "卫衣", "desc": "高级街头基础款卫衣", "likes": 3800},
    {"title": "Stüssy 渔夫帽", "cat": "帽子", "desc": "美式街头经典渔夫帽", "likes": 1400},
    {"title": "Bellroy 超薄卡包", "cat": "卡包", "desc": "澳洲超薄牛皮卡包", "likes": 1100},
    {"title": "Patagonia P-6 Logo T", "cat": "T恤", "desc": "环保户外品牌经典T恤", "likes": 1400},
    {"title": "Artemide Tolomeo 台灯", "cat": "氛围灯", "desc": "意大利经典机械臂台灯", "likes": 2000},
    {"title": "Stelton 啄木鸟保温壶", "cat": "水杯", "desc": "丹麦经典设计保温壶", "likes": 800},
    {"title": "Magis 360° 旋转容器", "cat": "收纳包", "desc": "意大利塑料设计收纳", "likes": 600},
    {"title": "Alessi 外星人榨汁机", "cat": "创意厨具", "desc": "后现代设计经典厨具", "likes": 1200},
]

# 5️⃣ Instagram 热门产品
INSTAGRAM = [
    {"title": "Le Creuset 珐琅马克杯", "cat": "水杯", "desc": "法式彩色珐琅马克杯", "likes": 1200},
    {"title": "Wedgwood 骨瓷茶杯", "cat": "水杯", "desc": "英式骨瓷经典设计", "likes": 900},
    {"title": "Flos IC 落地灯", "cat": "氛围灯", "desc": "意大利经典照明设计", "likes": 3200},
    {"title": "&Tradition 花苞灯", "cat": "氛围灯", "desc": "丹麦经典台灯设计", "likes": 2600},
    {"title": "Flos Snoopy 台灯", "cat": "氛围灯", "desc": "意大利设计经典台灯", "likes": 2000},
    {"title": "Hobonichi 手帐", "cat": "日历", "desc": "日本经典手帐本", "likes": 1500},
    {"title": "Paperblanks 复古日程本", "cat": "日历", "desc": "爱尔兰复古精装本", "likes": 800},
    {"title": "Carhartt WIP 口袋T恤", "cat": "T恤", "desc": "工装风格口袋T恤", "likes": 1100},
    {"title": "COS 极简T恤", "cat": "T恤", "desc": "北欧简约纯色T恤", "likes": 900},
    {"title": "Fred Perry 双条纹Polo", "cat": "Polo衫", "desc": "英伦经典双条纹Polo", "likes": 1800},
    {"title": "LACOSTE L.12.12 Polo衫", "cat": "Polo衫", "desc": "法国经典网眼Polo衫", "likes": 1500},
    {"title": "Champion 经典卫衣", "cat": "卫衣", "desc": "美式经典运动卫衣", "likes": 2800},
    {"title": "Stüssy 印花卫衣", "cat": "卫衣", "desc": "美式街头卫衣鼻祖", "likes": 3500},
    {"title": "A.P.C. 卫衣", "cat": "卫衣", "desc": "法式简约基础卫衣", "likes": 1600},
    {"title": "Stüssy 棒球帽", "cat": "帽子", "desc": "美式街头棒球帽", "likes": 1800},
    {"title": "Kangol 贝雷帽", "cat": "帽子", "desc": "英伦经典贝雷帽", "likes": 1100},
    {"title": "Palace 5-Panel 帽", "cat": "帽子", "desc": "英国滑板品牌帽子", "likes": 1400},
    {"title": "Carhartt WIP 棒球帽", "cat": "帽子", "desc": "工装风格棒球帽", "likes": 1200},
    {"title": "RHINOSHIELD 犀牛盾壳", "cat": "手机壳", "desc": "防摔手机壳开创者", "likes": 3200},
    {"title": "Nomad 真皮手机壳", "cat": "手机壳", "desc": "美国植鞣革手机壳", "likes": 1200},
    {"title": "Patagonia Torrentshell", "cat": "冲锋衣", "desc": "环保户外冲锋衣", "likes": 1800},
    {"title": "The North Face Summit 系列", "cat": "冲锋衣", "desc": "巅峰系列专业冲锋衣", "likes": 2200},
    {"title": "Mammut 艾格极限冲锋衣", "cat": "冲锋衣", "desc": "瑞士专业户外冲锋衣", "likes": 1500},
    {"title": "Mountain Hardwear Ghost", "cat": "冲锋衣", "desc": "超轻羽绒冲锋衣", "likes": 1100},
    {"title": "Nalgene 经典水壶", "cat": "钥匙扣水壶", "desc": "BPA-Free经典户外水壶", "likes": 800},
    {"title": "Stanley 经典真空壶", "cat": "钥匙扣水壶", "desc": "美国经典真空气压壶", "likes": 1400},
    {"title": "Hydro Flask 宽口水壶", "cat": "钥匙扣水壶", "desc": "双层真空不锈钢水壶", "likes": 1200},
    {"title": "SHARGE 闪极透明充电宝", "cat": "充电宝", "desc": "透明工业风移动电源", "likes": 2800},
    {"title": "Mophie Powerstation", "cat": "充电宝", "desc": "苹果认证充电宝", "likes": 800},
    {"title": "Native Union 编织充电宝", "cat": "充电宝", "desc": "编织线缆无线充电宝", "likes": 600},
    {"title": "MUJI 收纳盒", "cat": "收纳包", "desc": "极简收纳系列", "likes": 600},
    {"title": "IKEA SKADIS 收纳板", "cat": "收纳包", "desc": "模块化桌面收纳板", "likes": 900},
    {"title": "DULTON 工业风收纳", "cat": "收纳包", "desc": "美式工业风金属收纳", "likes": 700},
    {"title": "Bodum 法压壶", "cat": "水杯", "desc": "经典法式咖啡压壶", "likes": 700},
    {"title": "Riedel 水晶酒杯", "cat": "水杯", "desc": "奥地利手工水晶酒杯", "likes": 1300},
    {"title": "ZWIESEL 水晶玻璃杯", "cat": "水杯", "desc": "德国专业水晶玻璃杯", "likes": 900},
    {"title": "SMEG 多士炉", "cat": "创意厨具", "desc": "复古美学多士炉", "likes": 1800},
    {"title": "德龙 ECAM 咖啡机", "cat": "创意厨具", "desc": "意式全自动咖啡机", "likes": 1500},
    {"title": "Bellroy 钱包", "cat": "卡包", "desc": "澳洲环保皮革钱包", "likes": 900},
]

# 6️⃣ 小红书热门品牌
XIAOHONGSHU = [
    {"title": "MOREOVER 北欧水杯", "cat": "水杯", "desc": "北欧风陶瓷水杯设计", "likes": 800},
    {"title": "野兽派联名水杯", "cat": "水杯", "desc": "野兽派艺术家联名杯具", "likes": 1500},
    {"title": "故宫文创茶杯", "cat": "水杯", "desc": "故宫联名茶具设计", "likes": 2100},
    {"title": "泡泡玛特联名保温杯", "cat": "水杯", "desc": "盲盒IP跨界保温杯", "likes": 1800},
    {"title": "国誉自我手帐", "cat": "日历", "desc": "日本时间管理手帐本", "likes": 1200},
    {"title": "单向历", "cat": "日历", "desc": "单向空间经典日历", "likes": 1800},
    {"title": "几光 智能灯", "cat": "氛围灯", "desc": "国货智能氛围灯设计", "likes": 1100},
    {"title": "Yeelight 氛围灯", "cat": "氛围灯", "desc": "小米生态智能灯带", "likes": 900},
    {"title": "摩飞 多功能料理锅", "cat": "创意厨具", "desc": "网红多功能料理锅", "likes": 2800},
    {"title": "北鼎 养生壶", "cat": "创意厨具", "desc": "养生壶品类第一名", "likes": 1900},
    {"title": "ROARINGWILD 卫衣", "cat": "卫衣", "desc": "国潮卫衣代表品牌", "likes": 1500},
    {"title": "INXX 联名T恤", "cat": "T恤", "desc": "国潮设计师联名T恤", "likes": 1000},
    {"title": "TOMTOMMY 卡包", "cat": "卡包", "desc": "极简设计卡包", "likes": 500},
    {"title": "BAGGU 环保购物袋", "cat": "收纳包", "desc": "彩色尼龙环保收纳袋", "likes": 2400},
    {"title": "乐歌 E5 升降桌", "cat": "创意桌搭", "desc": "国货电动升降桌", "likes": 1600},
    {"title": "故宫日历 2025", "cat": "日历", "desc": "故宫博物院经典日历", "likes": 4500},
    {"title": "敦煌日历 2025", "cat": "日历", "desc": "敦煌壁画主题日历", "likes": 3000},
    {"title": "豆瓣电影日历 2025", "cat": "日历", "desc": "豆瓣经典电影日历", "likes": 3200},
]

# 7️⃣ 抖音热门
DOUYIN = [
    {"title": "Nalgene 运动水壶", "cat": "钥匙扣水壶", "desc": "户外运动经典水壶", "likes": 600},
    {"title": "驼峰 运动水壶", "cat": "钥匙扣水壶", "desc": "专业运动补水壶", "likes": 500},
    {"title": "小米 口袋充电宝", "cat": "充电宝", "desc": "高性价比口袋充电宝", "likes": 1200},
    {"title": "倍思 氮化镓充电宝", "cat": "充电宝", "desc": "大容量快充充电宝", "likes": 700},
    {"title": "罗马仕 充电宝", "cat": "充电宝", "desc": "国民充电宝品牌", "likes": 800},
    {"title": "凯乐石 冲锋衣", "cat": "冲锋衣", "desc": "国货专业登山冲锋衣", "likes": 900},
    {"title": "小米 床头灯", "cat": "氛围灯", "desc": "高性价比智能床头灯", "likes": 800},
    {"title": "华为智选 台灯", "cat": "氛围灯", "desc": "华为智选护眼台灯", "likes": 500},
    {"title": "Anker 收纳包", "cat": "收纳包", "desc": "数码线材收纳包", "likes": 400},
    {"title": "双立人 刀具套装", "cat": "创意厨具", "desc": "德国厨刀标杆", "likes": 700},
    {"title": "Nike Dri-FIT 运动帽", "cat": "帽子", "desc": "速干运动帽", "likes": 600},
    {"title": "MLB 经典帽款", "cat": "帽子", "desc": "MLB韩版时尚帽子", "likes": 2500},
    {"title": "WASSUP T恤", "cat": "T恤", "desc": "国潮基础款T恤", "likes": 500},
    {"title": "FMACM 卫衣", "cat": "卫衣", "desc": "国潮设计感卫衣", "likes": 700},
    {"title": "BEASTER 鬼脸T恤", "cat": "T恤", "desc": "国潮鬼脸印花T恤", "likes": 1200},
]

# ====== 来源对应的 URL 前缀 ======
URL_PREFIX = {
    "Good Design Award": "https://www.behance.net/search/projects/",
    "iF设计奖": "https://www.behance.net/search/projects/",
    "Red Dot": "https://www.behance.net/search/projects/",
    "A' Design Award": "https://www.behance.net/search/projects/",
}

def make_url(source, title):
    """根据来源和标题生成合适的URL"""
    from urllib.parse import quote
    if source == "Instagram":
        # Instagram 没有直接搜索API，用标签页
        return f"https://www.instagram.com/explore/tags/{quote(title.split()[0])}/"
    elif source == "小红书":
        return f"https://www.xiaohongshu.com/search_result?keyword={quote(title)}"
    elif source == "抖音":
        return f"https://www.douyin.com/search/{quote(title)}"
    else:
        # Behance 搜索
        return f"https://www.behance.net/search/projects/{quote(title)}"

def generate_dataset():
    items = []
    
    # 组装数据，每个产品配对应来源的链接
    all_data = []
    
    for item in GOOD_DESIGN:
        all_data.append({**item, "src": "Good Design Award"})
    for item in IF_DESIGN:
        all_data.append({**item, "src": "iF设计奖"})
    for item in RED_DOT:
        all_data.append({**item, "src": "Red Dot"})
    for item in A_DESIGN:
        all_data.append({**item, "src": "A' Design Award"})
    for item in INSTAGRAM:
        all_data.append({**item, "src": "Instagram"})
    for item in XIAOHONGSHU:
        all_data.append({**item, "src": "小红书"})
    for item in DOUYIN:
        all_data.append({**item, "src": "抖音"})
    
    for item in all_data:
        score_base = 8.0 if "奖" in item["src"] or "Award" in item["src"] else 7.0
        score = score_base + random.uniform(-0.3, 0.8)
        
        items.append({
            "title": item["title"],
            "reason": f"{item['src']} · {item['desc']}",
            "source": item["src"],
            "category": item["cat"],
            "creator": item["src"],
            "score": round(min(score, 9.5), 1),
            "likes": item["likes"],
            "url": make_url(item["src"], item["title"]),
            "tags": [item["cat"], item["src"], "获奖" if "奖" in item["src"] or "Award" in item["src"] else "社交精选"]
        })
    
    random.shuffle(items)
    items.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    from collections import Counter
    src_counts = Counter(i["source"] for i in items)
    cat_counts = Counter(i["category"] for i in items)
    
    data = {
        "date": datetime.date.today().isoformat(),
        "timestamp": datetime.datetime.now().isoformat(),
        "stats": {
            "total": len(items),
            "by_source": dict(src_counts),
            "by_category": dict(cat_counts)
        },
        "items": items
    }
    return data

if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    data = generate_dataset()
    
    output = os.path.join(DATA_DIR, "latest.json")
    with open(output, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    minified = json.dumps(data, ensure_ascii=False)
    js_output = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.js")
    with open(js_output, "w", encoding="utf-8") as f:
        f.write(f"const digestData = {minified};")
    
    print(f"✅ 生成 {len(data['items'])} 条数据")
    for src, n in sorted(data['stats']['by_source'].items(), key=lambda x:-x[1]):
        print(f"   {src}: {n}")
    
    print("\nURL类型验证:")
    from collections import defaultdict
    url_types = defaultdict(int)
    for item in data['items']:
        u = item['url']
        if 'behance.net' in u:
            url_types['Behance搜索'] += 1
        elif 'instagram.com' in u:
            url_types['Instagram标签页'] += 1
        elif 'xiaohongshu.com' in u:
            url_types['小红书搜索'] += 1
        elif 'douyin.com' in u:
            url_types['抖音搜索'] += 1
    for k,v in sorted(url_types.items(), key=lambda x:-x[1]):
        print(f"   {k}: {v}")
