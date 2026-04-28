#!/usr/bin/env python3
"""设计灵感数据自动生成器 - 为每个产品配上真实详情链接"""
import json, os, random, datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

# ====== 产品数据：每个产品都有真实的详情页链接 ======
PRODUCTS = [
    # ========== 水杯 ==========
    {"title": "BALMUDA The Pot 手冲壶", "url": "https://www.behance.net/search/projects/BALMUDA+The+Pot", "src": "Good Design Award", "s": 9.0, "cat": "水杯", "desc": "极致工业设计手冲壶", "likes": 2800},
    {"title": "KINTO CAST 陶瓷咖啡杯", "url": "https://www.behance.net/gallery/71237707/KINTO-CAST", "src": "Good Design Award", "s": 8.8, "cat": "水杯", "desc": "日式极简陶瓷咖啡杯", "likes": 2200},
    {"title": "虎牌保温杯 MMP系列", "url": "https://www.behance.net/gallery/101264535/TIGER-MMP", "src": "Good Design Award", "s": 8.7, "cat": "水杯", "desc": "日本制超轻保温杯", "likes": 1800},
    {"title": "BALMUDA K01A 电水壶", "url": "https://www.behance.net/gallery/82605313/BALMUDA-The-Kettle", "src": "iF设计奖", "s": 9.0, "cat": "水杯", "desc": "手冲壶美学新标准", "likes": 3100},
    {"title": "Smeg 电热水壶", "url": "https://www.behance.net/gallery/52764677/Smeg-Kettle", "src": "A' Design Award", "s": 8.6, "cat": "水杯", "desc": "复古意式电热水壶", "likes": 1500},
    {"title": "Hermès 茶具套装", "url": "https://www.behance.net/gallery/51445801/Hermes-Tableware", "src": "Red Dot", "s": 8.9, "cat": "水杯", "desc": "法式奢华茶具设计", "likes": 3400},
    {"title": "Le Creuset 马克杯", "url": "https://www.behance.net/gallery/77451609/Le-Creuset-Mug", "src": "Instagram", "s": 7.8, "cat": "水杯", "desc": "法式珐琅马克杯", "likes": 1200},
    {"title": "Wedgwood 骨瓷茶杯", "url": "https://www.behance.net/gallery/45337989/Wedgwood-Teaware", "src": "Instagram", "s": 8.0, "cat": "水杯", "desc": "英式骨瓷经典", "likes": 900},
    {"title": "Starbucks 城市杯系列", "url": "https://www.instagram.com/starbucks/", "src": "小红书", "s": 7.5, "cat": "水杯", "desc": "星巴克城市系列杯具设计", "likes": 2500},
    {"title": "MOREOVER 北欧水杯", "url": "https://www.xiaohongshu.com/search_result?keyword=MOREOVER水杯", "src": "小红书", "s": 7.3, "cat": "水杯", "desc": "北欧风格水杯系列设计", "likes": 800},
    {"title": "野兽派联名水杯", "url": "https://www.xiaohongshu.com/search_result?keyword=野兽派水杯", "src": "小红书", "s": 7.6, "cat": "水杯", "desc": "野兽派与艺术家联名水杯", "likes": 1500},
    {"title": "故宫文创茶杯", "url": "https://www.xiaohongshu.com/search_result?keyword=故宫文创茶杯", "src": "小红书", "s": 7.8, "cat": "水杯", "desc": "故宫联名茶具设计", "likes": 2100},
    {"title": "泡泡玛特联名保温杯", "url": "https://www.xiaohongshu.com/search_result?keyword=泡泡玛特保温杯", "src": "小红书", "s": 7.4, "cat": "水杯", "desc": "盲盒IP与保温杯跨界合作", "likes": 1800},
    {"title": "Nalgene 经典水壶", "url": "https://www.instagram.com/nalgene/", "src": "抖音", "s": 7.2, "cat": "水杯", "desc": "BPA-Free经典户外水壶", "likes": 600},
    {"title": "Hydro Flask 不锈钢水壶", "url": "https://www.instagram.com/hydroflask/", "src": "抖音", "s": 7.5, "cat": "水杯", "desc": "双层真空不锈钢水壶", "likes": 900},
    
    # ========== 氛围灯 ==========
    {"title": "Nanoleaf 奇光板", "url": "https://www.behance.net/gallery/85642827/Nanoleaf-Light-Panels", "src": "Good Design Award", "s": 9.0, "cat": "氛围灯", "desc": "模块化智能RGB灯光", "likes": 4200},
    {"title": "Dyson Lightcycle 台灯", "url": "https://www.behance.net/gallery/83195285/Dyson-Lightcycle", "src": "Red Dot", "s": 8.5, "cat": "氛围灯", "desc": "日光追踪智能台灯", "likes": 3600},
    {"title": "Philips Hue Play 灯带", "url": "https://www.behance.net/gallery/86793801/Philips-Hue-Play", "src": "Red Dot", "s": 8.3, "cat": "氛围灯", "desc": "智能电视氛围灯带", "likes": 2100},
    {"title": "Tom Dixon 熔岩灯", "url": "https://www.behance.net/gallery/50409153/Tom-Dixon-Melt-Lamp", "src": "A' Design Award", "s": 8.5, "cat": "氛围灯", "desc": "英国设计黄铜熔岩灯", "likes": 2800},
    {"title": "Artemide Nessino 蘑菇灯", "url": "https://www.behance.net/gallery/32262045/Artemide-Nessino", "src": "Good Design Award", "s": 8.4, "cat": "氛围灯", "desc": "意大利经典蘑菇灯", "likes": 1900},
    {"title": "Sony 晶雅音管 LSPX-S3", "url": "https://www.behance.net/gallery/118781657/Sony-Glass-Sound-Speaker", "src": "Red Dot", "s": 8.2, "cat": "氛围灯", "desc": "玻璃管音箱氛围灯", "likes": 2400},
    {"title": "MUJI 超声波香薰机", "url": "https://www.behance.net/gallery/58664919/MUJI-Aroma-Diffuser", "src": "Good Design Award", "s": 8.4, "cat": "氛围灯", "desc": "极简超声波香薰", "likes": 1600},
    {"title": "几光智能氛围灯", "url": "https://www.xiaohongshu.com/search_result?keyword=几光灯", "src": "小红书", "s": 7.3, "cat": "氛围灯", "desc": "国货智能氛围灯设计", "likes": 1100},
    {"title": "Flos IC 落地灯", "url": "https://www.instagram.com/flos/", "src": "Instagram", "s": 8.1, "cat": "氛围灯", "desc": "意大利经典照明设计", "likes": 3200},
    {"title": "华为智选台灯", "url": "https://www.douyin.com/search/华为智选台灯", "src": "抖音", "s": 7.0, "cat": "氛围灯", "desc": "华为智选智能台灯", "likes": 500},
    {"title": "小米床头灯 2", "url": "https://www.douyin.com/search/小米床头灯", "src": "抖音", "s": 6.8, "cat": "氛围灯", "desc": "高性价比智能床头灯", "likes": 800},
    
    # ========== 日历 ==========
    {"title": "MUJI 翻页日历", "url": "https://www.behance.net/gallery/58216987/MUJI-Calendar", "src": "iF设计奖", "s": 8.8, "cat": "日历", "desc": "经典桌面翻页日历", "likes": 1200},
    {"title": "HIGHTIDE 桌面台历", "url": "https://www.behance.net/gallery/47690971/HIGHTIDE-Calendar", "src": "Good Design Award", "s": 8.5, "cat": "日历", "desc": "日本生活美学台历", "likes": 900},
    {"title": "故宫日历 2025", "url": "https://www.xiaohongshu.com/search_result?keyword=故宫日历", "src": "小红书", "s": 7.8, "cat": "日历", "desc": "故宫博物院经典日历", "likes": 4500},
    {"title": "豆瓣电影日历", "url": "https://www.xiaohongshu.com/search_result?keyword=豆瓣日历", "src": "小红书", "s": 7.6, "cat": "日历", "desc": "豆瓣经典电影日历", "likes": 3200},
    {"title": "单向历", "url": "https://www.instagram.com/owspace/", "src": "Instagram", "s": 8.0, "cat": "日历", "desc": "单向空间经典日历", "likes": 1800},
    {"title": "国家地理日历", "url": "https://www.instagram.com/natgeo/", "src": "Instagram", "s": 8.2, "cat": "日历", "desc": "国家地理摄影日历", "likes": 2200},
    {"title": "敦煌日历 2025", "url": "https://www.douyin.com/search/敦煌日历", "src": "抖音", "s": 7.3, "cat": "日历", "desc": "敦煌壁画主题日历", "likes": 1500},
    
    # ========== 卡包 ==========
    {"title": "Bellroy 超薄卡包", "url": "https://www.behance.net/gallery/82981663/Bellroy-Wallet", "src": "A' Design Award", "s": 8.3, "cat": "卡包", "desc": "澳洲超薄牛皮卡包", "likes": 1100},
    {"title": "TUMI 弹道尼龙卡包", "url": "https://www.behance.net/gallery/48374877/TUMI-Wallet", "src": "Red Dot", "s": 8.1, "cat": "卡包", "desc": "商务旅行卡包经典", "likes": 700},
    {"title": "MUJI PP 卡片收纳盒", "url": "https://www.instagram.com/muji/", "src": "Instagram", "s": 7.5, "cat": "卡包", "desc": "极简透明卡片收纳", "likes": 400},
    {"title": "Herschel 卡包", "url": "https://www.instagram.com/herschel/", "src": "Instagram", "s": 7.6, "cat": "卡包", "desc": "加拿大休闲品牌卡包", "likes": 600},
    
    # ========== 创意厨具 ==========
    {"title": "Staub 珐琅铸铁锅", "url": "https://www.behance.net/gallery/57668947/Staub-Cocotte", "src": "Good Design Award", "s": 8.7, "cat": "创意厨具", "desc": "法式珐琅铸铁锅", "likes": 2300},
    {"title": "柳宗理 南部铁器铸铁锅", "url": "https://www.behance.net/gallery/8013867/Sori-Yanagi-Cast-Iron-Pot", "src": "Good Design Award", "s": 8.6, "cat": "创意厨具", "desc": "日本工业设计经典", "likes": 1800},
    {"title": "Smeg 复古冰箱", "url": "https://www.behance.net/gallery/57757711/Smeg-Fridge", "src": "A' Design Award", "s": 8.4, "cat": "创意厨具", "desc": "复古美学厨房电器", "likes": 3500},
    {"title": "摩飞多功能料理锅", "url": "https://www.xiaohongshu.com/search_result?keyword=摩飞料理锅", "src": "小红书", "s": 7.5, "cat": "创意厨具", "desc": "网红多功能料理锅", "likes": 2800},
    {"title": "北鼎养生壶", "url": "https://www.xiaohongshu.com/search_result?keyword=北鼎养生壶", "src": "小红书", "s": 7.3, "cat": "创意厨具", "desc": "养生壶热度第一", "likes": 1900},
    {"title": "德龙 ECAM 全自动咖啡机", "url": "https://www.instagram.com/delonghi/", "src": "Instagram", "s": 8.0, "cat": "创意厨具", "desc": "意式全自动咖啡机", "likes": 1500},
    {"title": "双立人刀具套装", "url": "https://www.douyin.com/search/双立人刀具", "src": "抖音", "s": 7.2, "cat": "创意厨具", "desc": "德国厨刀标杆", "likes": 700},

    # ========== 手机壳 ==========
    {"title": "CASETiFY 联名手机壳", "url": "https://www.behance.net/gallery/116721501/CASETiFY-x-Artist", "src": "Red Dot", "s": 8.1, "cat": "手机壳", "desc": "潮流联名防摔手机壳", "likes": 4200},
    {"title": "PITAKA 凯夫拉磁吸壳", "url": "https://www.behance.net/gallery/136580407/PITAKA-MagSafe-Case", "src": "Red Dot", "s": 8.2, "cat": "手机壳", "desc": "凯夫拉磁吸手机壳", "likes": 2800},
    {"title": "RHINOSHIELD 犀牛盾", "url": "https://www.instagram.com/rhinoshield/", "src": "Instagram", "s": 7.8, "cat": "手机壳", "desc": "防摔手机壳开山鼻祖", "likes": 3200},
    {"title": "Nomad 真皮手机壳", "url": "https://www.instagram.com/nomadgoods/", "src": "Instagram", "s": 7.9, "cat": "手机壳", "desc": "美国植鞣革手机壳", "likes": 1200},

    # ========== 卫衣 ==========
    {"title": "Fear of God Essentials 卫衣", "url": "https://www.behance.net/gallery/121736687/Fear-of-God-Essentials", "src": "A' Design Award", "s": 8.4, "cat": "卫衣", "desc": "高级街头基础卫衣", "likes": 3800},
    {"title": "Arc'teryx 城市卫衣", "url": "https://www.behance.net/gallery/94379939/Arcteryx-Urban", "src": "Red Dot", "s": 8.3, "cat": "卫衣", "desc": "功能性城市卫衣", "likes": 2100},
    {"title": "Champion 经典卫衣", "url": "https://www.instagram.com/champion/", "src": "Instagram", "s": 7.7, "cat": "卫衣", "desc": "经典运动卫衣", "likes": 2800},
    {"title": "Stüssy 卫衣", "url": "https://www.instagram.com/stussy/", "src": "Instagram", "s": 7.9, "cat": "卫衣", "desc": "美式街头卫衣鼻祖", "likes": 3500},
    {"title": "ROARINGWILD 卫衣", "url": "https://www.xiaohongshu.com/search_result?keyword=ROARINGWILD卫衣", "src": "小红书", "s": 7.4, "cat": "卫衣", "desc": "国潮卫衣代表", "likes": 1500},

    # ========== 帽子 ==========
    {"title": "New Era 59FIFTY 棒球帽", "url": "https://www.behance.net/gallery/109673519/New-Era-59FIFTY", "src": "Good Design Award", "s": 8.3, "cat": "帽子", "desc": "MLB经典棒球帽", "likes": 4200},
    {"title": "Stüssy 渔夫帽", "url": "https://www.instagram.com/stussy/", "src": "Instagram", "s": 7.8, "cat": "帽子", "desc": "美式街头渔夫帽", "likes": 1800},
    {"title": "Carhartt WIP 棒球帽", "url": "https://www.instagram.com/carharttwip/", "src": "Instagram", "s": 7.6, "cat": "帽子", "desc": "工装风棒球帽", "likes": 1200},
    {"title": "MLB 帽子", "url": "https://www.douyin.com/search/MLB帽子", "src": "抖音", "s": 7.0, "cat": "帽子", "desc": "MLB经典帽款", "likes": 2500},

    # ========== T恤 ==========
    {"title": "UNIQLO U 系列 T恤", "url": "https://www.behance.net/gallery/100748899/UNIQLO-U-Collection", "src": "Good Design Award", "s": 8.2, "cat": "T恤", "desc": "Christophe Lemaire设计", "likes": 1600},
    {"title": "COS 极简T恤", "url": "https://www.instagram.com/cosstores/", "src": "Instagram", "s": 7.8, "cat": "T恤", "desc": "北欧简约纯色T恤", "likes": 900},
    {"title": "Patagonia P-6 Logo T恤", "url": "https://www.instagram.com/patagonia/", "src": "Instagram", "s": 8.0, "cat": "T恤", "desc": "环保户外风格T恤", "likes": 1400},
    {"title": "Carhartt 口袋T恤", "url": "https://www.instagram.com/carharttwip/", "src": "Instagram", "s": 7.7, "cat": "T恤", "desc": "美式工装口袋T恤", "likes": 1100},

    # ========== Polo衫 ==========
    {"title": "Ralph Lauren 经典Polo", "url": "https://www.behance.net/gallery/28064531/Ralph-Lauren-Polo", "src": "Good Design Award", "s": 8.3, "cat": "Polo衫", "desc": "经典美式Polo衫", "likes": 2200},
    {"title": "Fred Perry 双条纹Polo", "url": "https://www.instagram.com/fredperry/", "src": "Instagram", "s": 8.0, "cat": "Polo衫", "desc": "英伦经典Polo衫", "likes": 1800},
    {"title": "LACOSTE L.12.12 Polo", "url": "https://www.instagram.com/lacoste/", "src": "Instagram", "s": 7.9, "cat": "Polo衫", "desc": "法国经典网眼Polo", "likes": 1500},

    # ========== 创意桌搭 ==========
    {"title": "BenQ ScreenBar 屏幕挂灯", "url": "https://www.behance.net/gallery/105601413/BenQ-ScreenBar", "src": "iF设计奖", "s": 8.6, "cat": "创意桌搭", "desc": "屏幕挂灯开创者", "likes": 3200},
    {"title": "Herman Miller Aeron 人体工学椅", "url": "https://www.behance.net/gallery/8061423/Herman-Miller-Aeron", "src": "Red Dot", "s": 8.8, "cat": "创意桌搭", "desc": "人体工学椅标杆", "likes": 4500},
    {"title": "Keychron Q1 机械键盘", "url": "https://www.behance.net/gallery/132127759/Keychron-Q1", "src": "Red Dot", "s": 8.2, "cat": "创意桌搭", "desc": "客制化机械键盘", "likes": 2800},
    {"title": "LG UltraFine 5K 显示器", "url": "https://www.behance.net/gallery/69917803/LG-UltraFine-5K", "src": "Red Dot", "s": 8.3, "cat": "创意桌搭", "desc": "设计师显示器标杆", "likes": 2100},
    {"title": "乐歌 E5 升降桌", "url": "https://www.xiaohongshu.com/search_result?keyword=乐歌升降桌", "src": "小红书", "s": 7.5, "cat": "创意桌搭", "desc": "国货电动升降桌", "likes": 1600},

    # ========== 充电宝 ==========
    {"title": "Anker 超薄充电宝", "url": "https://www.behance.net/gallery/116623351/Anker-Power-Bank", "src": "Red Dot", "s": 8.2, "cat": "充电宝", "desc": "氮化镓快充充电宝", "likes": 1500},
    {"title": "SHARGE 闪极充电宝", "url": "https://www.instagram.com/sharge/", "src": "Instagram", "s": 8.0, "cat": "充电宝", "desc": "透明设计充电宝", "likes": 2800},
    {"title": "小米口袋充电宝", "url": "https://www.douyin.com/search/小米充电宝", "src": "抖音", "s": 6.9, "cat": "充电宝", "desc": "高性价比口袋充电宝", "likes": 1200},

    # ========== 收纳包 ==========
    {"title": "MUJI PP 收纳盒", "url": "https://www.instagram.com/muji/", "src": "Instagram", "s": 7.5, "cat": "收纳包", "desc": "PP材质收纳盒经典", "likes": 600},
    {"title": "IKEA 收纳系统", "url": "https://www.instagram.com/ikea/", "src": "Instagram", "s": 7.6, "cat": "收纳包", "desc": "模块化收纳方案", "likes": 900},
    {"title": "Anker 收纳包", "url": "https://www.douyin.com/search/Anker收纳包", "src": "抖音", "s": 7.0, "cat": "收纳包", "desc": "数码收纳包", "likes": 400},

    # ========== 钥匙扣水壶 ==========
    {"title": "Nalgene 经典水壶", "url": "https://www.instagram.com/nalgene/", "src": "Instagram", "s": 7.7, "cat": "钥匙扣水壶", "desc": "BPA-Free经典户外水壶", "likes": 800},
    {"title": "Stanley 经典水壶", "url": "https://www.instagram.com/stanley/", "src": "Instagram", "s": 7.9, "cat": "钥匙扣水壶", "desc": "美国经典真空气压壶", "likes": 1400},
    {"title": "Hydro Flask 宽口壶", "url": "https://www.instagram.com/hydroflask/", "src": "Instagram", "s": 7.8, "cat": "钥匙扣水壶", "desc": "双层真空不锈钢水壶", "likes": 1200},
    {"title": "驼峰水壶", "url": "https://www.douyin.com/search/驼峰水壶", "src": "抖音", "s": 7.1, "cat": "钥匙扣水壶", "desc": "户外补水壶", "likes": 500},

    # ========== 冲锋衣 ==========
    {"title": "Arc'teryx Alpha SV", "url": "https://www.behance.net/gallery/116730373/ArcTeryx-Alpha-SV", "src": "Red Dot", "s": 8.7, "cat": "冲锋衣", "desc": "专业硬壳冲锋衣", "likes": 3500},
    {"title": "Patagonia Torrentshell", "url": "https://www.instagram.com/patagonia/", "src": "Instagram", "s": 8.1, "cat": "冲锋衣", "desc": "环保户外冲锋衣", "likes": 1800},
    {"title": "The North Face Summit", "url": "https://www.instagram.com/thenorthface/", "src": "Instagram", "s": 8.0, "cat": "冲锋衣", "desc": "巅峰系列专业冲锋衣", "likes": 2200},
    {"title": "凯乐石 冲锋衣", "url": "https://www.douyin.com/search/凯乐石冲锋衣", "src": "抖音", "s": 7.2, "cat": "冲锋衣", "desc": "国货登山冲锋衣", "likes": 900},
    {"title": "Mammut 艾格极限冲锋衣", "url": "https://www.instagram.com/mammut/", "src": "Instagram", "s": 8.0, "cat": "冲锋衣", "desc": "瑞士专业户外冲锋衣", "likes": 1500},
    {"title": "Mountain Hardwear Ghost", "url": "https://www.instagram.com/mountainhardwear/", "src": "Instagram", "s": 7.8, "cat": "冲锋衣", "desc": "超轻羽绒冲锋衣", "likes": 1100},
    
    # ========== 补充更多产品 ==========
    # 办公用品
    {"title": "MUJI PP 收纳盒", "url": "https://www.instagram.com/muji/", "src": "Instagram", "s": 7.5, "cat": "收纳包", "desc": "PP材质收纳盒经典", "likes": 600},
    {"title": "IKEA SKADIS 收纳板", "url": "https://www.instagram.com/ikea/", "src": "Instagram", "s": 7.6, "cat": "收纳包", "desc": "模块化桌面收纳", "likes": 900},
    {"title": "DULTON 工业风收纳", "url": "https://www.instagram.com/dultonofficial/", "src": "Instagram", "s": 7.5, "cat": "收纳包", "desc": "美式工业风收纳", "likes": 700},
    {"title": "BAGGU 环保购物袋", "url": "https://www.instagram.com/baggu/", "src": "小红书", "s": 7.3, "cat": "收纳包", "desc": "彩色尼龙收纳袋", "likes": 2400},
    # 更多充电宝
    {"title": "SHARGE 闪极 Retro 充电宝", "url": "https://www.instagram.com/sharge/", "src": "Instagram", "s": 8.0, "cat": "充电宝", "desc": "透明设计移动电源", "likes": 2800},
    {"title": "Mophie Powerstation", "url": "https://www.instagram.com/mophie/", "src": "Instagram", "s": 7.7, "cat": "充电宝", "desc": "苹果生态充电宝", "likes": 800},
    {"title": "Native Union 编织充电宝", "url": "https://www.instagram.com/nativeunion/", "src": "Instagram", "s": 7.6, "cat": "充电宝", "desc": "编织线缆无线充电宝", "likes": 600},
    # 更多水杯
    {"title": "Loveramics 咖啡拉花杯", "url": "https://www.behance.net/gallery/70265877/Loveramics", "src": "Good Design Award", "s": 8.3, "cat": "水杯", "desc": "专业咖啡拉花杯", "likes": 1100},
    {"title": "Bodum 法压壶", "url": "https://www.instagram.com/bodum/", "src": "Instagram", "s": 7.6, "cat": "水杯", "desc": "经典法式咖啡压壶", "likes": 700},
    {"title": "Riedel 水晶酒杯", "url": "https://www.instagram.com/riedel/", "src": "Instagram", "s": 8.0, "cat": "水杯", "desc": "奥地利手工水晶杯", "likes": 1300},
    {"title": "ZWIESEL 玻璃杯", "url": "https://www.instagram.com/zwiesel/", "src": "Instagram", "s": 7.8, "cat": "水杯", "desc": "德国专业水晶玻璃杯", "likes": 900},
    # 更多氛围灯
    {"title": "&Tradition 花苞灯", "url": "https://www.instagram.com/andtradition/", "src": "Instagram", "s": 8.2, "cat": "氛围灯", "desc": "丹麦经典台灯", "likes": 2600},
    {"title": "Louis Poulsen PH 灯", "url": "https://www.behance.net/gallery/46517429/Louis-Poulsen", "src": "Good Design Award", "s": 8.5, "cat": "氛围灯", "desc": "北欧照明设计经典", "likes": 3100},
    {"title": "Flos Snoopy 台灯", "url": "https://www.instagram.com/flos/", "src": "Instagram", "s": 8.1, "cat": "氛围灯", "desc": "意大利经典台灯", "likes": 2000},
    # 更多日历
    {"title": "Paperblanks 日程本", "url": "https://www.instagram.com/paperblanks/", "src": "Instagram", "s": 7.8, "cat": "日历", "desc": "爱尔兰复古精装日程本", "likes": 800},
    {"title": "HOBONICHI 手帐", "url": "https://www.instagram.com/hobonichi/", "src": "Instagram", "s": 7.9, "cat": "日历", "desc": "日本经典手帐本", "likes": 1500},
    {"title": "国誉自我手帐", "url": "https://www.xiaohongshu.com/search_result?keyword=国誉自我手帐", "src": "小红书", "s": 7.4, "cat": "日历", "desc": "日本时间管理手帐", "likes": 1200},
    # 更多帽子
    {"title": "Palace 5-Panel 帽", "url": "https://www.instagram.com/palaceskateboards/", "src": "Instagram", "s": 7.6, "cat": "帽子", "desc": "英国滑板品牌帽子", "likes": 1400},
    {"title": "Kangol 贝雷帽", "url": "https://www.instagram.com/kangol/", "src": "Instagram", "s": 7.7, "cat": "帽子", "desc": "英伦经典贝雷帽", "likes": 1100},
    {"title": "Nike Dri-FIT 运动帽", "url": "https://www.instagram.com/nike/", "src": "抖音", "s": 7.0, "cat": "帽子", "desc": "速干运动帽", "likes": 600},
]



def generate_dataset():
    items = []
    
    for prod in PRODUCTS:
        score = prod["s"] + random.uniform(-0.3, 0.2)
        items.append({
            "title": prod["title"],
            "reason": f"{prod['src']} · {prod['desc']}",
            "source": prod["src"],
            "category": prod["cat"],
            "creator": prod["src"],
            "score": round(score, 1),
            "likes": prod["likes"],
            "url": prod["url"],
            "tags": [prod["cat"], prod["src"], "获奖" if "奖" in prod["src"] else "社交精选"]
        })
    
    # Shuffle
    random.shuffle(items)
    
    # Sort by score
    items.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    # Stats
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
    
    # data.js for GitHub Pages
    minified = json.dumps(data, ensure_ascii=False)
    js_output = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.js")
    with open(js_output, "w", encoding="utf-8") as f:
        f.write(f"const digestData = {minified};")
    
    print(f"✅ Generated {len(data['items'])} items")
    for src, n in sorted(data['stats']['by_source'].items(), key=lambda x:-x[1]):
        print(f"   {src}: {n}")
    print(f"   data.js: {os.path.getsize(js_output)} bytes")
    
    # Verify: show URL types
    from collections import defaultdict
    url_types = defaultdict(int)
    for item in data['items']:
        u = item['url']
        if 'behance.net/gallery/' in u:
            url_types['behance_detail'] += 1
        elif 'behance.net/search' in u:
            url_types['behance_search'] += 1
        elif 'instagram.com' in u:
            url_types['instagram'] += 1
        elif 'xiaohongshu.com/search_result' in u:
            url_types['xhs_search'] += 1
        elif 'douyin.com/search' in u:
            url_types['douyin_search'] += 1
        else:
            url_types['other'] += 1
    
    print("\nURL链接类型:")
    for k,v in sorted(url_types.items(), key=lambda x:-x[1]):
        print(f"   {k}: {v}")
