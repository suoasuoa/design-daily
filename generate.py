#!/usr/bin/env python3
"""
Daily Design Digest - 数据生成器
每个产品配精确的产品页链接和OG图片。
"""
import json, os, random, datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# (title, category, desc, url, image, likes)
# url: 精确产品页链接
# image: OG图片URL (可为空)

# Good Design Award (15 items)
GOOD_DESIGN = [
    ("Herman Miller Eames 休闲椅", "创意桌搭", "20世纪设计经典家具", "https://www.hermanmiller.com/products/seating/lounge-seating/eames-lounge-chair-and-ottoman/", "", 3800),
    ("MUJI 超声波香薰机", "氛围灯", "极简超声波香薰扩散器", "https://www.muji.com/jp/ja/store/cmdty/detail/4550344593967", "", 1600),
    ("MUJI PP 收纳盒", "收纳包", "经典PP材质收纳系列", "https://www.muji.com/jp/ja/store/cmdty/section/S107010101", "", 600),
    ("New Era 59FIFTY 棒球帽", "帽子", "MLB官方经典棒球帽", "https://www.neweracap.com/collections/59fifty-fitted", "", 4200),
    ("柳宗理 铸铁锅", "创意厨具", "日本工业设计大师经典", "https://www.soriyanagi.jp/product/ironware/", "", 1800),
    ("Artemide Nessino 蘑菇灯", "氛围灯", "意大利经典蘑菇灯设计", "https://www.artemide.com/en/products/table/nessino", "", 1900),
    ("虎牌保温杯 MMP系列", "水杯", "日本制超轻不锈钢保温杯", "https://www.tiger-corporation.com/ja/jpn/product/tumbler/", "", 1800),
    ("Ralph Lauren 经典Polo衫", "Polo衫", "美式经典Polo衫设计", "https://www.ralphlauren.com/men-clothing-polo-shirts", "", 2200),
    ("UNIQLO U 系列T恤", "T恤", "Christophe Lemaire设计", "https://www.uniqlo.com/us/en/c/uniqlo-u-collection/", "", 1600),
    ("Stelton 啄木鸟保温壶", "水杯", "丹麦现代经典保温壶", "https://www.stelton.com/en/em77-vacuum-jug-1l-soft-black", "", 800),
    ("HIGHTIDE 桌面台历", "日历", "日本生活美学桌面台历", "https://hightide.jp/c/desktop-accessories/calendar", "", 900),
    ("Louis Poulsen PH灯", "氛围灯", "北欧照明设计经典之作", "https://www.louispoulsen.com/en/catalog/private/pendants/ph-5", "", 3100),
    ("Staub 珐琅铸铁锅", "创意厨具", "法式经典珐琅铸铁锅", "https://www.staub.com/us/cocotte", "", 2300),
    ("KINTO CAST 陶瓷咖啡杯", "水杯", "日式极简陶瓷咖啡杯", "https://kinto-global.com/collections/cast/", "", 2200),
    ("Loveramics 咖啡拉花杯", "水杯", "专业咖啡拉花杯多色釉面", "https://www.loveramics.com/collections/latte-art", "", 1100),
]

# iF设计奖 (10 items)
IF_DESIGN = [
    ("BenQ ScreenBar 屏幕挂灯", "创意桌搭", "屏幕挂灯品类开创者", "https://www.benq.com/en-us/lighting/monitor-light/screenbar.html", "https://image.benq.com/is/image/benqco/07screenbar-topleft45-button-3?$ResponsivePreset$", 3200),
    ("BALMUDA The Pot 手冲壶", "水杯", "极致工业设计手冲电水壶", "https://www.balmuda.com/jp/pot", "https://www.balmuda.com/jp/pot/img/og/index.jpg", 2800),
    ("Philips 千禧台灯", "氛围灯", "LED照明设计创新之作", "https://www.philips.com/c-m/lighting/led-lights", "", 1400),
    ("Nio 蔚来 EP9", "氛围灯", "电动超跑设计理念", "https://www.nio.com/ep9", "", 4500),
    ("大疆 Mavic 无人机", "创意桌搭", "折叠无人机工业设计典范", "https://www.dji.com/mavic-3-pro", "https://www-cdn.djiits.com/cms/uploads/ff6ae7f2efed6d80de477f6a634d6c4b@374*374.png", 3500),
    ("Dyson Supersonic 吹风机", "创意厨具", "重新定义吹风机工业设计", "https://www.dyson.com/hair-care/hair-dryers/supersonic", "", 5600),
    ("Oculus Quest 2", "创意桌搭", "VR一体机工业设计", "https://www.meta.com/quest/", "", 2100),
    ("Sonos One 音箱", "氛围灯", "智能WiFi音箱工业设计", "https://www.sonos.com/en-us/shop/one", "https://media.sonos.com/images/znqtjj88/production/41da7c5be257ce106bb5e40f6d83e860e3b3eacb-848x848.png?q=75&amp;fit=clip&amp;auto=format", 1800),
    ("BALMUDA K01A 电水壶", "水杯", "手冲壶美学全新标准", "https://www.balmuda.com/jp/pot", "", 3100),
    ("MUJI 翻页日历", "日历", "经典极简桌面翻页日历", "https://www.muji.com/jp/ja/store/cmdty/section/S107030204", "", 1200),
]

# Red Dot (14 items)
RED_DOT = [
    ("Keychron Q1 机械键盘", "创意桌搭", "客制化铝制机械键盘", "https://www.keychron.com/products/keychron-q1", "http://www.keychron.com/cdn/shop/products/Keychron-Q1-QMK-VIA-custom-mechanical-keyboard-75-percent-layout-full-aluminum-black-frame-for-Mac-Windows-iOS-RGB-backlight-with-hot-swappable-Gateron-G-Pro-switch-red.jpg?crop=center&height=1200&v=1657854465&width=1200", 2800),
    ("Philips Hue Play 灯带", "氛围灯", "智能电视氛围灯带", "https://www.philips-hue.com/en-us/p/hue-play-light-bar/7820131U7", "", 2100),
    ("Arc'teryx Alpha SV 冲锋衣", "冲锋衣", "专业级硬壳冲锋衣", "https://arcteryx.com/shop/alpha-sv-jacket", "", 3500),
    ("CASETiFY 防摔手机壳", "手机壳", "联名艺术防摔手机壳", "https://www.casetify.com/", "https://ctgimage1.s3.amazonaws.com/cms/image/6fa327bd55bdbbba4d13e3339edadbdd.png", 4200),
    ("Sony 晶雅音管 LSPX-S3", "氛围灯", "玻璃管音箱与氛围灯结合", "https://www.sony.com/en/articles/product-specifications-lspx-s3", "", 2400),
    ("Dyson Lightcycle 台灯", "氛围灯", "日光追踪智能LED台灯", "https://www.dyson.com/lighting/desk-lights/solarcycle-morph", "", 3600),
    ("Moshi 笔记本内胆包", "收纳包", "极简设计笔记本包", "https://www.moshi.com/en/category/bags", "https://cdn.shopify.com/s/files/1/0569/8666/5098/collections/6c593ca3688cb0cfa492c39b.jpg?v=1648463949", 500),
    ("Anker GaN 充电器", "充电宝", "氮化镓快充充电器", "https://www.anker.com/collections/chargers", "https://cdn.shopify.com/s/files/1/0493/9834/9974/collections/screenshot-20250225-162633_2c0a754b-03a0-4585-97e8-6da8c4049f43.png?v=1740472040", 1500),
    ("LG UltraFine 5K 显示器", "创意桌搭", "设计师专业显示器", "https://www.lg.com/us/monitors/lg-27md5kl-b-5k-702702", "", 2100),
    ("PITAKA 凯夫拉手机壳", "手机壳", "凯夫拉芳纶纤维磁吸壳", "https://www.pitaka.com/collections/magez-case", "", 2800),
    ("Herman Miller Aeron 椅", "创意桌搭", "人体工学椅行业标杆", "https://www.hermanmiller.com/products/seating/office-chairs/aeron-chairs/", "https://www.hermanmiller.com/content/dam/hmicom/page_assets/products/aeron_chair/202106/og_office_chairs_aeron_chair.jpg", 4500),
    ("Hermès 茶具套装", "水杯", "法式奢华陶瓷茶具", "https://www.hermes.com/us/en/category/home/tableware/tea/", "", 3400),
    ("TUMI 弹道尼龙公文包", "卡包", "商务旅行箱包标杆", "https://www.tumi.com/c/alpha-bravo/", "", 700),
    ("Smeg 复古冰箱", "创意厨具", "复古美学厨房电器", "https://www.smeg.com/refrigerators", "https://www.smeg.com/binaries/content/gallery/smeg/categories/frigoriferi-2.jpg/frigoriferi-2.jpg/brx%3ApostcardDeskLarge", 3500),
]

# A' Design Award (10 items)
A_DESIGN = [
    ("Smeg 电热水壶", "水杯", "复古意式电热水壶", "https://www.smeg.com/kettles", "https://www.smeg.com/binaries/content/gallery/smeg/categories/sda_smeg_frontale_klf.jpg/sda_smeg_frontale_klf.jpg/brx%3ApostcardDeskLarge", 1500),
    ("Fear of God Essentials", "卫衣", "高级街头基础款卫衣", "https://fearofgod.com/collections/essentials", "", 3800),
    ("Stüssy 渔夫帽", "帽子", "美式街头经典渔夫帽", "https://www.stussy.com/collections/headwear", "http://www.stussy.com/cdn/shop/files/checkout-logo_256x256_c8c5b294-3bd0-4d8e-a5bd-e4066efcc662.png?v=1678808251", 1400),
    ("Vans 经典滑板鞋", "帽子", "美式滑板鞋设计", "https://www.vans.com/en-us/categories/classic-shoes-old-skool", "", 2000),
    ("Alessi 外星人榨汁机", "创意厨具", "后现代设计经典厨具", "https://www.alessi.com/products/juicy-salif", "", 1200),
    ("Magis 360° 旋转容器", "收纳包", "意大利塑料设计收纳", "https://www.magisdesign.com/product/360-container/", "", 600),
    ("Patagonia P-6 Logo T", "T恤", "环保户外品牌经典T恤", "https://www.patagonia.com/product/mens-p-6-logo-responsibili-tee/38504.html", "https://www.patagonia.com/dw/image/v2/BDJB_PRD/on/demandware.static/-/Sites-patagonia-master/default/dwffc443ac/images/hi-res/38504_POGM.jpg?sw=256&amp;sh=256&amp;sfrm=png&amp;q=95&amp;bgcolor=f3f4ef", 1400),
    ("Tom Dixon 熔岩灯", "氛围灯", "英国设计黄铜熔岩灯", "https://www.tomdixon.net/en/lighting/melt.html", "", 2800),
    ("Bellroy 超薄卡包", "卡包", "澳洲超薄牛皮卡包", "https://bellroy.com/products/slim-sleeve-wallet", "https://bellroy-product-images.imgix.net//bellroy_dot_com_gallery_image/USD/WSSB-CJA-101/0", 1100),
    ("Artemide Tolomeo 台灯", "氛围灯", "意大利经典机械臂台灯", "https://www.artemide.com/en/products/table/tolomeo", "", 2000),
]

# Instagram (39 items)
INSTAGRAM = [
    ("COS 极简T恤", "T恤", "北欧简约纯色T恤", "https://www.cosstores.com/en/men/t-shirts.html", "", 900),
    ("SHARGE 闪极透明充电宝", "充电宝", "透明工业风移动电源", "https://www.sharge.com/products/retro-67", "http://sharge.com/cdn/shop/files/Retro67GaNCharger_4c90d722-1258-487c-b9e3-e158de744150.png?v=1772714414", 2800),
    ("Stanley 经典真空壶", "钥匙扣水壶", "美国经典真空气压壶", "https://www.stanley1913.com/collections/iceflow", "https://www.stanley1913.com/cdn/shop/files/Stanley_Horizontal_x320_b3ec2ef4-fa76-454a-b900-c4055137902d.webp?height=628&pad_color=fff&v=1706751331&width=1200", 1400),
    ("Paperblanks 复古日程本", "日历", "爱尔兰复古精装本", "https://www.paperblanks.com/collections/planners", "", 800),
    ("Mammut 艾格极限冲锋衣", "冲锋衣", "瑞士专业户外冲锋衣", "https://www.mammut.com/int/en/cat/230-hardshell-jackets-men/", "https://images.ctfassets.net/l595fda2nfqd/493aXEg31Defo62SW4Wtk5/4e0f3fbf01a21bf774773e3e11094cda/hiking_ducan-spine_rgb_03895.jpg?fm=jpg&amp;w=512&amp;q=80", 1500),
    ("Le Creuset 珐琅马克杯", "水杯", "法式彩色珐琅马克杯", "https://www.lecreuset.com/coffee-and-tea/mugs-cups/", "", 1200),
    ("Nalgene 经典水壶", "钥匙扣水壶", "BPA-Free经典户外水壶", "https://nalgene.com/product/32oz-wide-mouth-sustain/", "https://nalgene.com/wp-content/uploads/2025/12/nalgene-water-bottles.jpg", 800),
    ("Flos Snoopy 台灯", "氛围灯", "意大利设计经典台灯", "https://www.flos.com/en/products/decorative/snoopy", "", 2000),
    ("Hydro Flask 宽口水壶", "钥匙扣水壶", "双层真空不锈钢水壶", "https://www.hydroflask.com/wide-mouth-with-flex-cap-32", "", 1200),
    ("Wedgwood 骨瓷茶杯", "水杯", "英式骨瓷经典设计", "https://www.wedgwood.com/en-us/dining/drinkware/teacups-saucers/", "", 900),
    ("Champion 经典卫衣", "卫衣", "美式经典运动卫衣", "https://www.champion.com/collections/reverse-weave", "http://www.champion.com/cdn/shop/files/1200x628-1.jpg?v=1770045447&width=1024", 2800),
    ("Bodum 法压壶", "水杯", "经典法式咖啡压壶", "https://www.bodum.com/us/en/french-press", "", 700),
    ("Fred Perry 双条纹Polo", "Polo衫", "英伦经典双条纹Polo", "https://www.fredperry.com/the-fred-perry-shirt", "", 1800),
    ("Nomad 真皮手机壳", "手机壳", "美国植鞣革手机壳", "https://www.nomadgoods.com/collections/cases", "https://cdn.shopify.com/s/files/1/0384/6721/files/apple-watch-natural-metal-band-front.jpg?v=1728060667&amp;width=1280&amp;height=630", 1200),
    ("Stüssy 印花卫衣", "卫衣", "美式街头卫衣鼻祖", "https://www.stussy.com/collections/sweatshirts", "", 3500),
    ("Hobonichi 手帐", "日历", "日本经典手帐本", "https://www.1101.com/store/techo/en/", "https://www.1101.com/store/techo/2026/images/og/techo2026_en.jpg", 1500),
    ("Stüssy 棒球帽", "帽子", "美式街头棒球帽", "https://www.stussy.com/collections/headwear", "http://www.stussy.com/cdn/shop/files/checkout-logo_256x256_c8c5b294-3bd0-4d8e-a5bd-e4066efcc662.png?v=1678808251", 1800),
    ("Native Union 编织充电宝", "充电宝", "编织线缆无线充电宝", "https://www.nativeunion.com/collections/power", "", 600),
    ("MUJI 收纳盒", "收纳包", "极简收纳系列", "https://www.muji.com/jp/ja/store/cmdty/section/S107010101", "", 600),
    ("IKEA SKADIS 收纳板", "收纳包", "模块化桌面收纳板", "https://www.ikea.com/us/en/cat/skadis-series-37813/", "https://www.ikea.com/global/assets/range-categorisation/images/skadis-series-37813.jpeg", 900),
    ("Kangol 贝雷帽", "帽子", "英伦经典贝雷帽", "https://www.kangol.com/collections/berets", "http://kangol.com/cdn/shop/files/kangolLogo-og-rectangle.png?v=1727455664", 1100),
    ("ZWIESEL 水晶玻璃杯", "水杯", "德国专业水晶玻璃杯", "https://www.zwiesel.com/en/glassware/wine-glasses/", "", 900),
    ("Carhartt WIP 口袋T恤", "T恤", "美式工装风格口袋T恤", "https://www.carhartt-wip.com/en/men-tshirts", "https://www.carhartt-wip.com/og-image.png", 1100),
    ("Carhartt WIP 棒球帽", "帽子", "工装风格棒球帽", "https://www.carhartt-wip.com/en/men-accessories-hats-and-caps", "https://www.carhartt-wip.com/og-image.png", 1200),
    ("Riedel 水晶酒杯", "水杯", "奥地利手工水晶酒杯", "https://www.riedel.com/en-us/shop/wine-glasses", "https://img.riedel.com/w_1200,h_600,q_80,v_dde8f4,hash_af8e84/dam/4000x2100px-Header-Site-n-XXL-Teaser-n-Hero-Product-Teaser-n-Related-Products-Teaser/RIEDEL/2022/2022-Genussletter-November_Fankhauser/4000x2100px_LIA_8271_special-usage-only.jpg", 1300),
    ("A.P.C. 卫衣", "卫衣", "法式简约基础卫衣", "https://www.apc.fr/categories/men/sweatshirts", "", 1600),
    ("Palace 5-Panel 帽", "帽子", "英国滑板品牌帽子", "https://www.palaceskateboards.com/", "", 1400),
    ("德龙 ECAM 咖啡机", "创意厨具", "意式全自动咖啡机", "https://www.delonghi.com/en-us/coffee/coffee-machines/automatic-coffee-machines/", "", 1500),
    ("SMEG 多士炉", "创意厨具", "复古美学多士炉", "https://www.smeg.com/toasters", "https://www.smeg.com/binaries/content/gallery/smeg/categories/sda_smeg_frontale_tsf.jpg/sda_smeg_frontale_tsf.jpg/brx%3ApostcardDeskLarge", 1800),
    ("RHINOSHIELD 犀牛盾壳", "手机壳", "防摔手机壳开创者", "https://www.rhinoshield.com/collections/iphone-cases", "", 3200),
    ("DULTON 工业风收纳", "收纳包", "美式工业风金属收纳", "https://www.dulton.com/products/storage", "", 700),
    ("&Tradition 花苞灯", "氛围灯", "丹麦经典台灯设计", "https://www.andtradition.com/products/flowerpot-vp3", "https://wp.andtradition.com/wp-content/uploads/2025/11/133084A568_Flowerpot-VP3_Steel-Blue_Front_ON-1200x1200.jpg", 2600),
    ("Flos IC 落地灯", "氛围灯", "意大利经典照明设计", "https://www.flos.com/en/products/decorative/ic-lights", "", 3200),
    ("Bellroy 钱包", "卡包", "澳洲环保皮革钱包", "https://bellroy.com/products/hide-and-seek-wallet", "https://bellroy-product-images.imgix.net//bellroy_dot_com_gallery_image/USD/WHSD-CAR-301/0", 900),
    ("LACOSTE L.12.12 Polo衫", "Polo衫", "法国经典网眼Polo衫", "https://www.lacoste.com/us/men/clothing/polo-shirts/", "", 1500),
    ("The North Face Summit", "冲锋衣", "巅峰系列专业冲锋衣", "https://www.thenorthface.com/en-us/explore/summit-series", "", 2200),
    ("Patagonia Torrentshell", "冲锋衣", "环保户外冲锋衣", "https://www.patagonia.com/product/mens-torrentshell-3l-rain-jacket/85241.html", "https://www.patagonia.com/dw/image/v2/BDJB_PRD/on/demandware.static/-/Sites-patagonia-master/default/dw7138ee44/images/hi-res/85241_GEMG.jpg?sw=256&amp;sh=256&amp;sfrm=png&amp;q=95&amp;bgcolor=f3f4ef", 1800),
    ("Mophie Powerstation", "充电宝", "苹果认证充电宝", "https://www.mophie.com/collections/portable-power", "", 800),
    ("Mountain Hardwear Ghost", "冲锋衣", "超轻羽绒冲锋衣", "https://www.mountainhardwear.com/c/mens-jackets/", "", 1100),
]

# 小红书 (18 items)
XIAOHONGSHU = [
    ("乐歌 E5 升降桌", "创意桌搭", "国货电动升降桌", "https://www.loctek.com/", "", 1600),
    ("TOMTOMMY 卡包", "卡包", "极简设计卡包", "https://www.tomtommmy.com/", "", 500),
    ("泡泡玛特联名保温杯", "水杯", "盲盒IP跨界保温杯", "https://www.popmart.com/", "", 1800),
    ("INXX 联名T恤", "T恤", "国潮设计师联名T恤", "https://www.inxx.com/", "", 1000),
    ("几光 智能灯", "氛围灯", "国货智能氛围灯设计", "https://ezvalo.com/", "", 1100),
    ("敦煌日历 2025", "日历", "敦煌壁画主题日历", "https://www.dunhuang.com/", "", 3000),
    ("故宫文创茶杯", "水杯", "故宫联名茶具设计", "https://www.dpm.org.cn/", "https://img.dpm.org.cn/static/themes_wap/image/wechat_share1.png", 2100),
    ("MOREOVER 北欧水杯", "水杯", "北欧风陶瓷水杯设计", "https://moreover.cc", "", 800),
    ("国誉自我手帐", "日历", "日本时间管理手帐本", "https://www.kokuyo.com/en/", "/sites/default/files/shared_contents/wp-content/uploads/2021/10/bnr_jibuntecho_211001.jpg", 1200),
    ("野兽派联名水杯", "水杯", "野兽派与艺术家联名杯具", "https://www.thebeastshop.com/", "", 1500),
    ("Yeelight 氛围灯", "氛围灯", "小米生态智能灯带", "https://www.yeelight.com/", "", 900),
    ("ROARINGWILD 卫衣", "卫衣", "国潮卫衣代表品牌", "https://www.roaringwild.com/", "http://roaringwild.com/cdn/shop/files/ROARINGWILD_NEW_Logo_WH_1920_1080_1200x1200.jpg?v=1749110173", 1500),
    ("BAGGU 环保购物袋", "收纳包", "彩色尼龙环保收纳袋", "https://www.baggu.com/collections/standard-baggu", "https://cdn.sanity.io/images/t9jjg1v5/production/2b1638c7fbe8a9ab35a51af7e16edd972c3f5fbd-1200x630.png", 2400),
    ("故宫日历 2025", "日历", "故宫博物院经典日历", "https://www.dpm.org.cn/", "https://img.dpm.org.cn/static/themes_wap/image/wechat_share1.png", 4500),
    ("北鼎 养生壶", "创意厨具", "养生壶品类第一", "https://www.buydeem.com/", "", 1900),
    ("豆瓣电影日历", "日历", "豆瓣经典电影日历", "https://www.douban.com/", "", 3200),
    ("摩飞 多功能料理锅", "创意厨具", "网红多功能料理锅", "https://www.morphyrichards.com/", "http://morphyrichards.com/cdn/shop/files/Social_Image.jpg?v=1700278803", 2800),
    ("单向历", "日历", "单向空间经典日历", "https://www.owspace.com/", "", 1800),
]

# 抖音 (16 items)
DOUYIN = [
    ("驼峰 运动水壶", "钥匙扣水壶", "专业运动补水壶", "https://www.camelbak.com/recreation/bottles", "", 500),
    ("FMACM 卫衣", "卫衣", "国潮设计感卫衣", "https://www.fmacm.com/", "", 700),
    ("Nike Dri-FIT 运动帽", "帽子", "速干运动帽", "https://www.nike.com/w/hats-and-headwear-9zy6f", "https://www.nike.com/android-icon-192x192.png", 600),
    ("Anker 收纳包", "收纳包", "数码线材收纳包", "https://www.anker.com/collections/all-accessories", "", 400),
    ("华为智选 台灯", "氛围灯", "华为智选护眼台灯", "https://www.huawei.com/", "https://www-file.huawei.com/-/media/corp/home/image/logo_400x200.png", 500),
    ("倍思 氮化镓充电宝", "充电宝", "大容量快充充电宝", "https://www.baseus.com/collections/power-banks", "http://www.baseus.com/cdn/shop/collections/Baseus_Elf_Power_Bank_65W_20000mAh_1_front_side_700x_65bd1d66-3ba4-4b64-a8c7-3b0d52204a14.webp?v=1677744576", 700),
    ("小米 床头灯", "氛围灯", "高性价比智能床头灯", "https://www.mi.com/", "", 800),
    ("Nalgene 运动水壶", "钥匙扣水壶", "户外运动经典水壶", "https://nalgene.com/product/32oz-wide-mouth-sustain/", "https://nalgene.com/wp-content/uploads/2025/12/nalgene-water-bottles.jpg", 600),
    ("MLB 经典帽款", "帽子", "MLB韩版时尚帽子", "https://www.mlbbrand.com/", "", 2500),
    ("BOTTLED JOY 吨吨桶", "水杯", "网红大容量运动水壶", "https://bottledjoy.com/", "http://bottledjoy.com/cdn/shop/files/5b6u5L_h5Zu_54mHXzIwMjMwNjEzMTY0NTMzLnBuZw.png?v=1686880714", 1800),
    ("小米 口袋充电宝", "充电宝", "高性价比口袋充电宝", "https://www.mi.com/", "", 1200),
    ("双立人 刀具套装", "创意厨具", "德国厨刀标杆", "https://www.zwilling.com/us/cutlery/knives/", "", 700),
    ("WASSUP T恤", "T恤", "国潮基础款T恤", "https://www.wassup.com/", "", 500),
    ("凯乐石 冲锋衣", "冲锋衣", "国货专业登山冲锋衣", "https://www.kailas.com/", "", 900),
    ("罗马仕 充电宝", "充电宝", "国民充电宝品牌", "https://www.romoss.com/", "", 800),
    ("BEASTER 鬼脸T恤", "T恤", "国潮鬼脸印花T恤", "https://www.beaster.com/", "", 1200),
]


def main():
    items = []
    all_data = []
    for title, cat, desc, url, image, likes in GOOD_DESIGN:
        all_data.append((title, cat, desc, url, image, likes, "Good Design Award"))
    for title, cat, desc, url, image, likes in IF_DESIGN:
        all_data.append((title, cat, desc, url, image, likes, "iF设计奖"))
    for title, cat, desc, url, image, likes in RED_DOT:
        all_data.append((title, cat, desc, url, image, likes, "Red Dot"))
    for title, cat, desc, url, image, likes in A_DESIGN:
        all_data.append((title, cat, desc, url, image, likes, "A' Design Award"))
    for title, cat, desc, url, image, likes in INSTAGRAM:
        all_data.append((title, cat, desc, url, image, likes, "Instagram"))
    for title, cat, desc, url, image, likes in XIAOHONGSHU:
        all_data.append((title, cat, desc, url, image, likes, "小红书"))
    for title, cat, desc, url, image, likes in DOUYIN:
        all_data.append((title, cat, desc, url, image, likes, "抖音"))

    for title, cat, desc, url, image, likes, source in all_data:
        score_base = 8.0 if ("奖" in source or "Award" in source) else 7.2
        score = score_base + random.uniform(-0.2, 0.6)
        entry = {
            "title": title,
            "reason": f"{source} · {desc}",
            "source": source,
            "category": cat,
            "creator": source,
            "score": round(min(score, 9.5), 1),
            "likes": likes,
            "url": url,
            "tags": [cat, source, "获奖" if ("奖" in source or "Award" in source) else "社交精选"]
        }
        if image:
            entry["image"] = image
        items.append(entry)

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

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, "latest.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    minified = json.dumps(data, ensure_ascii=False)
    with open(os.path.join(os.path.dirname(__file__), "data.js"), "w", encoding="utf-8") as f:
        f.write(f"const digestData = {minified};")

    has_img = sum(1 for i in items if i.get("image"))
    print(f"✅ {len(items)} 条 | {len(src_counts)} 来源 | {len(cat_counts)} 品类 | {has_img} 有图片")
    for src, n in sorted(src_counts.items(), key=lambda x: -x[1]):
        print(f"   {src}: {n}")


if __name__ == "__main__":
    main()
