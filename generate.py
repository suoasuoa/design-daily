#!/usr/bin/env python3
"""
Daily Design Digest - 数据自动生成器
包含精确产品页链接、OG图片、19个品类、9个来源
"""
import json, os, random, datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# Tuple: (title, category, desc, url, image, likes)

# Good Design Award (28 items)
GOOD_DESIGN = [
    ("Louis Poulsen PH灯", "氛围灯", "北欧照明设计经典之作", "https://www.louispoulsen.com/en/catalog/private/pendants/ph-5", "", 3100),
    ("Loveramics 咖啡拉花杯", "水杯", "专业咖啡拉花杯多色釉面", "https://www.loveramics.com/collections/latte-art", "", 1100),
    ("teamLab 数字装置", "装置艺术", "teamLab沉浸式数字艺术装置", "https://www.teamlab.art/", "https://www.teamlab.art/teamlab-art-ogp-image.png", 703),
    ("Secrid Cardprotector", "卡包", "荷兰铝制防RFID卡包", "https://www.secrid.com/en/products/cardprotector", "", 4299),
    ("MUJI 超声波香薰机", "氛围灯", "极简超声波香薰扩散器", "https://www.muji.com/jp/ja/store/cmdty/detail/4550344593967", "", 1600),
    ("UNIQLO U 系列T恤", "T恤", "Christophe Lemaire设计", "https://www.uniqlo.com/us/en/c/uniqlo-u-collection/", "", 1600),
    ("Staub 珐琅铸铁锅", "创意厨具", "法式经典珐琅铸铁锅", "https://www.staub.com/us/cocotte", "", 2300),
    ("KINTO CAST 陶瓷咖啡杯", "水杯", "日式极简陶瓷咖啡杯", "https://kinto-global.com/collections/cast/", "", 2200),
    ("Ralph Lauren 经典Polo衫", "Polo衫", "美式经典Polo衫设计", "https://www.ralphlauren.com/men-clothing-polo-shirts", "", 2200),
    ("HIGHTIDE 桌面台历", "日历", "日本生活美学桌面台历", "https://hightide.jp/c/desktop-accessories/calendar", "", 900),
    ("虎牌保温杯 MMP系列", "水杯", "日本制超轻不锈钢保温杯", "https://www.tiger-corporation.com/ja/jpn/product/tumbler/", "", 1800),
    ("伊势半 月见礼盒", "中秋礼盒", "日本传统月见节礼盒包装", "https://www.isehan.jp/", "", 2704),
    ("虎屋 端午限定礼盒", "端午礼盒", "京都虎屋端午柏饼礼盒", "https://www.toraya-group.co.jp/", "", 1236),
    ("New Era 59FIFTY 棒球帽", "帽子", "MLB官方经典棒球帽", "https://www.neweracap.com/collections/59fifty-fitted", "", 4200),
    ("Herman Miller Eames 休闲椅", "创意桌搭", "20世纪设计经典家具", "https://www.hermanmiller.com/products/seating/lounge-seating/eames-lounge-chair-and-ottoman/", "", 3800),
    ("Stelton 啄木鸟保温壶", "水杯", "丹麦现代经典保温壶", "https://www.stelton.com/en/em77-vacuum-jug-1l-soft-black", "", 800),
    ("BALMUDA 礼盒套装", "创意礼盒", "BALMUDA家电礼盒组合", "https://www.balmuda.com/jp/gift/", "", 3819),
    ("Olafur Eliasson 气象装置", "装置艺术", "冰岛艺术家大型环境装置", "https://olafureliasson.net/", "https://res.cloudinary.com/olafureliasson-net/image/private/q_auto:eco,c_fit,h_640,w_640/img/blog/a-symphony-of-disappearing-sounds-for-the-great-salt-lake_37718.jpg", 1230),
    ("藤本壮介 森林装置", "装置艺术", "SANAA建筑事务所空气感装置", "https://www.sou-fujimoto.net/", "images/address_long.gif", 1533),
    ("KitchenAid 厨师机", "创意厨具", "美国KitchenAid经典台式厨师机", "https://www.kitchenaid.com/stand-mixers.html", "", 3999),
    ("柳宗理 铸铁锅", "创意厨具", "日本工业设计大师经典", "https://www.soriyanagi.jp/product/ironware/", "", 1800),
    ("HIGHTIDE 礼物礼盒系列", "创意礼盒", "日本生活方式品牌HIGHTIDE的礼物组合", "https://hightide.jp/c/gift/", "", 4459),
    ("Zojirushi 不锈钢保温杯", "水杯", "日本象印经典不锈钢保温杯", "https://www.zojirushi.com/app/product/spcc", "", 4297),
    ("Artemide Nessino 蘑菇灯", "氛围灯", "意大利经典蘑菇灯设计", "https://www.artemide.com/en/products/table/nessino", "", 1900),
    ("MUJI PP 收纳盒", "收纳包", "经典PP材质收纳系列", "https://www.muji.com/jp/ja/store/cmdty/section/S107010101", "", 600),
    ("虎屋 中秋限定礼盒", "中秋礼盒", "京都虎屋和果子中秋限定", "https://www.toraya-group.co.jp/", "https://cdn.shopify.com/s/files/1/0641/4503/1410/files/cover_105301.jpg?v=1750647415", 4144),
    ("UNIQLO UT 联名礼盒", "创意礼盒", "UT系列限定联名礼品套装", "https://www.uniqlo.com/us/en/c/feature/ut/", "", 2013),
    ("WMF 厨师刀", "创意厨具", "德国WMF不锈钢厨师刀", "https://www.wmf.com/en/cookware/knives/", "", 1497),
]

# iF设计奖 (20 items)
IF_DESIGN = [
    ("MUJI 翻页日历", "日历", "经典极简桌面翻页日历", "https://www.muji.com/jp/ja/store/cmdty/section/S107030204", "", 1200),
    ("Nio 蔚来 EP9", "氛围灯", "电动超跑设计理念", "https://www.nio.com/ep9", "", 4500),
    ("Alessi 设计礼盒", "创意礼盒", "意大利设计家居礼品套装", "https://www.alessi.com/en/gifts/", "", 2844),
    ("Autonomous SmartDesk", "创意桌搭", "全自动电动升降桌", "https://www.autonomous.ai/smartdesk", "https://cdn.autonomous.ai/production/ecm/260227/desk(2).webp", 2249),
    ("Sonos One 音箱", "氛围灯", "智能WiFi音箱工业设计", "https://www.sonos.com/en-us/shop/one", "https://media.sonos.com/images/znqtjj88/production/41da7c5be257ce106bb5e40f6d83e860e3b3eacb-848x848.png?q=75&amp;fit=clip&amp;auto=format", 1800),
    ("Es Devlin 舞台装置", "装置艺术", "英国舞台设计师大型装置艺术", "https://www.esdevlin.com/", "/_next/image?url=https%3A%2F%2Fcdn.sanity.io%2Fimages%2F5olj48ug%2Fproduction%2Fa6c7269fb06578a2ad0a8ee71345fc0842e530a5-10879x8239.jpg&amp;w=3840&amp;q=75", 4816),
    ("大疆 Mavic 无人机", "创意桌搭", "折叠无人机工业设计典范", "https://www.dji.com/mavic-3-pro", "https://www-cdn.djiits.com/cms/uploads/ff6ae7f2efed6d80de477f6a634d6c4b@374*374.png", 3500),
    ("八马茶业 中秋茶礼", "中秋礼盒", "八马茶业中秋限定礼品装", "https://www.bamatea.com/", "", 4665),
    ("中茶 端午茶礼", "端午礼盒", "中茶端午限定红茶礼盒", "https://www.chinatea.com.cn/", "", 3912),
    ("白南准 电视装置", "装置艺术", "视频艺术之父媒体装置", "https://www.paikstudios.com/", "http://static1.squarespace.com/static/5f63c7f8bb5d793914450c1d/t/5f6a2f323c139f60ef955ca4/1600794420962/10.jpg?format=1500w", 3181),
    ("Philips 千禧台灯", "氛围灯", "LED照明设计创新之作", "https://www.philips.com/c-m/lighting/led-lights", "", 1400),
    ("下关沱茶 端午礼盒", "端午礼盒", "云南下关沱茶端午限定装", "https://www.xgtea.com/", "", 4566),
    ("Dyson 限定礼盒", "创意礼盒", "Dyson节日限定吹风机礼盒", "https://www.dyson.com/gifts", "{{../this.product.primaryImageUrl}}?$responsive$&amp;fmt=png-alpha", 1464),
    ("Studio Drift 无人机装置", "装置艺术", "荷兰艺术家无人机灯光装置", "https://www.studiodrift.com/", "https://i0.wp.com/studiodrift.com/wp-content/uploads/2021/02/LOrfeo-NRO048-1.jpeg?fit=2500%2C1444&ssl=1", 4875),
    ("BenQ ScreenBar 屏幕挂灯", "创意桌搭", "屏幕挂灯品类开创者", "https://www.benq.com/en-us/lighting/monitor-light/screenbar.html", "https://image.benq.com/is/image/benqco/07screenbar-topleft45-button-3?$ResponsivePreset$", 3200),
    ("BALMUDA The Pot 手冲壶", "水杯", "极致工业设计手冲电水壶", "https://www.balmuda.com/jp/pot", "https://www.balmuda.com/jp/pot/img/og/index.jpg", 2800),
    ("Muji Gift 精选礼盒", "创意礼盒", "无印良品精选礼物套装", "https://www.muji.com/jp/ja/store/cmdty/section/S10801/", "https://www.muji.com/public/media/img/item/4548076074229_org.jpg?im=Resize%2Ctype%3Ddownsize%2Cwidth%3D160", 1326),
    ("BALMUDA K01A 电水壶", "水杯", "手冲壶美学全新标准", "https://www.balmuda.com/jp/pot", "", 3100),
    ("Oculus Quest 2", "创意桌搭", "VR一体机工业设计", "https://www.meta.com/quest/", "", 2100),
    ("Dyson Supersonic 吹风机", "创意厨具", "重新定义吹风机工业设计", "https://www.dyson.com/hair-care/hair-dryers/supersonic", "", 5600),
]

# Red Dot (24 items)
RED_DOT = [
    ("LG UltraFine 5K 显示器", "创意桌搭", "设计师专业显示器", "https://www.lg.com/us/monitors/lg-27md5kl-b-5k-702702", "", 2100),
    ("Herman Miller Aeron 椅", "创意桌搭", "人体工学椅行业标杆", "https://www.hermanmiller.com/products/seating/office-chairs/aeron-chairs/", "https://www.hermanmiller.com/content/dam/hmicom/page_assets/products/aeron_chair/202106/og_office_chairs_aeron_chair.jpg", 4500),
    ("Moshi 笔记本内胆包", "收纳包", "极简设计笔记本包", "https://www.moshi.com/en/category/bags", "https://cdn.shopify.com/s/files/1/0569/8666/5098/collections/6c593ca3688cb0cfa492c39b.jpg?v=1648463949", 500),
    ("草间弥生 无限镜屋", "装置艺术", "草间弥生无限镜像装置", "https://yayoikusama.com/", "", 703),
    ("Patchi 中秋巧克力礼盒", "中秋礼盒", "迪拜顶级巧克力中秋限定", "https://www.patchi.com/", "", 1068),
    ("Janet Echelman 网雕装置", "装置艺术", "大型户外网状雕塑装置", "https://www.echelman.com/", "", 2223),
    ("Nanoleaf 奇光版", "氛围灯", "模块化智能LED壁灯", "https://nanoleaf.com/en-US/products/nanoleaf-shapes/", "https://us-cdn.nanoleaf.me/assets/img/favicons/nanoleaf-small-icon.png", 1093),
    ("Smeg 复古冰箱", "创意厨具", "复古美学厨房电器", "https://www.smeg.com/refrigerators", "https://www.smeg.com/binaries/content/gallery/smeg/categories/frigoriferi-2.jpg/frigoriferi-2.jpg/brx%3ApostcardDeskLarge", 3500),
    ("Leo Villareal LED装置", "装置艺术", "美国艺术家LED灯光装置", "https://www.leovillareal.com/", "", 1142),
    ("Keychron Q1 机械键盘", "创意桌搭", "客制化铝制机械键盘", "https://www.keychron.com/products/keychron-q1", "http://www.keychron.com/cdn/shop/products/Keychron-Q1-QMK-VIA-custom-mechanical-keyboard-75-percent-layout-full-aluminum-black-frame-for-Mac-Windows-iOS-RGB-backlight-with-hot-swappable-Gateron-G-Pro-switch-red.jpg?crop=center&height=1200&v=1657854465&width=1200", 2800),
    ("CASETiFY 防摔手机壳", "手机壳", "联名艺术防摔手机壳", "https://www.casetify.com/", "https://ctgimage1.s3.amazonaws.com/cms/image/6fa327bd55bdbbba4d13e3339edadbdd.png", 4200),
    ("PITAKA 凯夫拉手机壳", "手机壳", "凯夫拉芳纶纤维磁吸壳", "https://www.pitaka.com/collections/magez-case", "", 2800),
    ("Zwiesel 水晶酒杯礼盒", "创意礼盒", "德国Zwiesel水晶玻璃酒杯组合", "https://www.zwiesel.com/en/corporate-gifts/", "", 2460),
    ("TUMI 弹道尼龙公文包", "卡包", "商务旅行箱包标杆", "https://www.tumi.com/c/alpha-bravo/", "", 700),
    ("Philips Hue Play 灯带", "氛围灯", "智能电视氛围灯带", "https://www.philips-hue.com/en-us/p/hue-play-light-bar/7820131U7", "", 2100),
    ("Sony 晶雅音管 LSPX-S3", "氛围灯", "玻璃管音箱与氛围灯结合", "https://www.sony.com/en/articles/product-specifications-lspx-s3", "", 2400),
    ("Philips Hue 灯泡套装", "氛围灯", "飞利浦Hue智能照明入门套装", "https://www.philips-hue.com/en-us/p/hue-white-and-color-ambiance/", "", 3951),
    ("Anker GaN 充电器", "充电宝", "氮化镓快充充电器", "https://www.anker.com/collections/chargers", "https://cdn.shopify.com/s/files/1/0493/9834/9974/collections/screenshot-20250225-162633_2c0a754b-03a0-4585-97e8-6da8c4049f43.png?v=1740472040", 1500),
    ("Hermès 茶具套装", "水杯", "法式奢华陶瓷茶具", "https://www.hermes.com/us/en/category/home/tableware/tea/", "", 3400),
    ("Le Creuset 礼盒", "创意礼盒", "法国珐琅锅品牌礼盒套装", "https://www.lecreuset.com/gift-guide", "", 1077),
    ("Arc'teryx Alpha SV 冲锋衣", "冲锋衣", "专业级硬壳冲锋衣", "https://arcteryx.com/shop/alpha-sv-jacket", "", 3500),
    ("Dyson Lightcycle 台灯", "氛围灯", "日光追踪智能LED台灯", "https://www.dyson.com/lighting/desk-lights/solarcycle-morph", "", 3600),
    ("Smeg 家电礼盒", "创意礼盒", "SMEG复古家电礼盒套装", "https://www.smeg.com/gifts", "", 2196),
    ("大益茶 中秋礼盒", "中秋礼盒", "大益普洱中秋限定礼盒", "https://www.dayigroup.com/", "", 3968),
]

# A' Design Award (18 items)
A_DESIGN = [
    ("Stüssy 渔夫帽", "帽子", "美式街头经典渔夫帽", "https://www.stussy.com/collections/headwear", "http://www.stussy.com/cdn/shop/files/checkout-logo_256x256_c8c5b294-3bd0-4d8e-a5bd-e4066efcc662.png?v=1678808251", 1400),
    ("Magis 360° 旋转容器", "收纳包", "意大利塑料设计收纳", "https://www.magisdesign.com/product/360-container/", "", 600),
    ("Artemide Tolomeo 台灯", "氛围灯", "意大利经典机械臂台灯", "https://www.artemide.com/en/products/table/tolomeo", "", 2000),
    ("Floral 蜡烛香味礼盒", "创意礼盒", "天然植物香氛蜡烛套装", "https://www.yankeecandle.com/gifts/", "", 1300),
    ("Random International 雨屋", "装置艺术", "沉浸式数字雨屋装置", "https://www.random-international.com/", "http://static1.squarespace.com/static/663ca532b3e3797d82159fe2/t/66572f3a9742b832945631fc/1716989754702/16_random_international_logo_black%2Btext_02.png?format=1500w", 2476),
    ("Tom Dixon 熔岩灯", "氛围灯", "英国设计黄铜熔岩灯", "https://www.tomdixon.net/en/lighting/melt.html", "", 2800),
    ("Patagonia P-6 Logo T", "T恤", "环保户外品牌经典T恤", "https://www.patagonia.com/product/mens-p-6-logo-responsibili-tee/38504.html", "https://www.patagonia.com/dw/image/v2/BDJB_PRD/on/demandware.static/-/Sites-patagonia-master/default/dwffc443ac/images/hi-res/38504_POGM.jpg?sw=256&amp;sh=256&amp;sfrm=png&amp;q=95&amp;bgcolor=f3f4ef", 1400),
    ("Smeg 电热水壶", "水杯", "复古意式电热水壶", "https://www.smeg.com/kettles", "https://www.smeg.com/binaries/content/gallery/smeg/categories/sda_smeg_frontale_klf.jpg/sda_smeg_frontale_klf.jpg/brx%3ApostcardDeskLarge", 1500),
    ("馥颂 中秋马卡龙礼盒", "中秋礼盒", "法国Fauchon中秋限定礼盒", "https://www.fauchon.com/us_en/", "", 2828),
    ("Ladurée 中秋礼盒", "中秋礼盒", "法国Ladurée马卡龙中秋礼盒", "https://www.laduree.com/", "http://laduree.com/cdn/shop/files/og-share.jpg?v=1741119817&width=1024", 1036),
    ("Vans 经典滑板鞋", "帽子", "美式滑板鞋设计", "https://www.vans.com/en-us/categories/classic-shoes-old-skool", "", 2000),
    ("Tom Dixon 设计礼盒", "创意礼盒", "英国设计师品牌家居礼品", "https://www.tomdixon.net/en/gifts.html", "", 4321),
    ("Stelton 保温壶礼盒", "创意礼盒", "丹麦设计品牌礼盒", "https://www.stelton.com/en/em77-vacuum-jug-1l-soft-black", "", 1620),
    ("Bellroy 超薄卡包", "卡包", "澳洲超薄牛皮卡包", "https://bellroy.com/products/slim-sleeve-wallet", "https://bellroy-product-images.imgix.net//bellroy_dot_com_gallery_image/USD/WSSB-CJA-101/0", 1100),
    ("Fear of God Essentials", "卫衣", "高级街头基础款卫衣", "https://fearofgod.com/collections/essentials", "", 3800),
    ("Alessi 外星人榨汁机", "创意厨具", "后现代设计经典厨具", "https://www.alessi.com/products/juicy-salif", "", 1200),
    ("NONOTAK 光音装置", "装置艺术", "法国光与声媒体装置", "https://www.nonotak.com/", "https://assets.cdn.cargocollective.com/408512/435754190620483103326993812115427328/arrow-up.svg?f3a4624d93", 2565),
    ("Sólfar Studios 宇宙装置", "装置艺术", "俄罗斯数字艺术家超现实装置", "https://www.solfar.com/", "http://static1.squarespace.com/static/556f16d7e4b0eafb6eb48e02/t/556f1890e4b0b5f32ba22d67/1433772248927/SolfarLogoWhiteHires.png?format=1500w", 612),
]

# Instagram (76 items)
INSTAGRAM = [
    ("Aēsop 护肤礼盒", "创意礼盒", "伊索旅行套装礼盒", "https://www.aesop.com/us/gifts/", "", 1273),
    ("Harney & Sons 端午茶", "端午礼盒", "美国高端散茶端午礼盒", "https://www.harney.com/", "https://www.harney.com/cdn/shop/files/ht-english-breakfast-tins_46.jpg?v=1722953544", 3623),
    ("Yeti Rambler 马克杯", "水杯", "美国YETI真空隔热不锈钢杯", "https://www.yeti.com/drinkware/rambler-mugs.html", "", 4728),
    ("Mammut Nordwand Pro", "冲锋衣", "Mammut Nordwand高山冲锋衣", "https://www.mammut.com/int/en/cat/230-hardshell-jackets-men/", "https://images.ctfassets.net/l595fda2nfqd/493aXEg31Defo62SW4Wtk5/4e0f3fbf01a21bf774773e3e11094cda/hiking_ducan-spine_rgb_03895.jpg?fm=jpg&amp;w=512&amp;q=80", 1184),
    ("Bellroy 钱包", "卡包", "澳洲环保皮革钱包", "https://bellroy.com/products/hide-and-seek-wallet", "https://bellroy-product-images.imgix.net//bellroy_dot_com_gallery_image/USD/WHSD-CAR-301/0", 900),
    ("Stanley 经典真空壶", "钥匙扣水壶", "美国经典真空气压壶", "https://www.stanley1913.com/collections/iceflow", "https://www.stanley1913.com/cdn/shop/files/Stanley_Horizontal_x320_b3ec2ef4-fa76-454a-b900-c4055137902d.webp?height=628&pad_color=fff&v=1706751331&width=1200", 1400),
    ("Champion 经典卫衣", "卫衣", "美式经典运动卫衣", "https://www.champion.com/collections/reverse-weave", "http://www.champion.com/cdn/shop/files/1200x628-1.jpg?v=1770045447&width=1024", 2800),
    ("ZWIESEL 水晶玻璃杯", "水杯", "德国专业水晶玻璃杯", "https://www.zwiesel.com/en/glassware/wine-glasses/", "", 900),
    ("DULTON 工业风收纳", "收纳包", "美式工业风金属收纳", "https://www.dulton.com/products/storage", "", 700),
    ("BYREDO 香氛礼盒", "创意礼盒", "瑞典小众香氛礼品套装", "https://www.byredo.com/us_en/gifts", "https://www.byredo.com/cdn-cgi/image/format=auto,quality=70/https://www.byredo.com/media/catalog/product/cache/538055185084634e259189a2a72f806b/b/y/byredo_ecom_giftcard__.jpg", 1538),
    ("TWG Tea 中秋礼盒", "中秋礼盒", "新加坡顶级茶叶中秋礼盒", "https://www.twgtea.com/", "https://media.twgtea.com/images/default-source/illustrations-icons/twg-logo/1200x630--twg-teas-logo.jpg?sfvrsn=45d40125_2", 4270),
    ("蔡国强 火药装置", "装置艺术", "中国艺术家火药爆破装置", "https://www.caiguoqiang.com/", "", 2822),
    ("SHARGE 闪极透明充电宝", "充电宝", "透明工业风移动电源", "https://www.sharge.com/products/retro-67", "http://sharge.com/cdn/shop/files/Retro67GaNCharger_4c90d722-1258-487c-b9e3-e158de744150.png?v=1772714414", 2800),
    ("Kangol 贝雷帽", "帽子", "英伦经典贝雷帽", "https://www.kangol.com/collections/berets", "http://kangol.com/cdn/shop/files/kangolLogo-og-rectangle.png?v=1727455664", 1100),
    ("Flos IC 落地灯", "氛围灯", "意大利经典照明设计", "https://www.flos.com/en/products/decorative/ic-lights", "", 3200),
    ("Ronnefeldt 端午茶礼", "端午礼盒", "德国顶级茶叶端午限定", "https://www.ronnefeldt.com/", "https://www.ronnefeldt.com/userdata/images/social_media_banners/390_smb_vorschaubild_teeshop_x.jpg", 4593),
    ("Sunspel 经典Polo衫", "Polo衫", "英国Sunspel经典全棉Polo衫", "https://www.sunspel.com/en-us/polo-shirts.html", "", 4403),
    ("Polo Ralph Lauren 经典Polo", "Polo衫", "Ralph Lauren美国经典Polo衫", "https://www.ralphlauren.com/men-clothing-polo-shirts", "", 4020),
    ("RHINOSHIELD 犀牛盾壳", "手机壳", "防摔手机壳开创者", "https://www.rhinoshield.com/collections/iphone-cases", "", 3200),
    ("A.P.C. 卫衣", "卫衣", "法式简约基础卫衣", "https://www.apc.fr/categories/men/sweatshirts", "", 1600),
    ("Carhartt WIP 口袋T恤", "T恤", "美式工装风格口袋T恤", "https://www.carhartt-wip.com/en/men-tshirts", "https://www.carhartt-wip.com/og-image.png", 1100),
    ("COS 极简T恤", "T恤", "北欧简约纯色T恤", "https://www.cosstores.com/en/men/t-shirts.html", "", 900),
    ("Fred Perry 双条纹Polo", "Polo衫", "英伦经典双条纹Polo", "https://www.fredperry.com/the-fred-perry-shirt", "", 1800),
    ("&Tradition 花苞灯", "氛围灯", "丹麦经典台灯设计", "https://www.andtradition.com/products/flowerpot-vp3", "https://wp.andtradition.com/wp-content/uploads/2025/11/133084A568_Flowerpot-VP3_Steel-Blue_Front_ON-1200x1200.jpg", 2600),
    ("Supreme Box Logo 卫衣", "卫衣", "Supreme经典Box Logo连帽卫衣", "https://www.supremenewyork.com/shop/all/sweatshirts", "", 925),
    ("Mackintosh 防水Polo", "Polo衫", "英国Mackintosh经典胶面Polo", "https://www.mackintosh.com/en/category/all-polo-shirts/", "", 777),
    ("Stüssy 印花卫衣", "卫衣", "美式街头卫衣鼻祖", "https://www.stussy.com/collections/sweatshirts", "", 3500),
    ("LACOSTE L.12.12 Polo衫", "Polo衫", "法国经典网眼Polo衫", "https://www.lacoste.com/us/men/clothing/polo-shirts/", "", 1500),
    ("Carhartt WIP 棒球帽", "帽子", "工装风格棒球帽", "https://www.carhartt-wip.com/en/men-accessories-hats-and-caps", "https://www.carhartt-wip.com/og-image.png", 1200),
    ("Flos Snoopy 台灯", "氛围灯", "意大利设计经典台灯", "https://www.flos.com/en/products/decorative/snoopy", "", 2000),
    ("Paperblanks 复古日程本", "日历", "爱尔兰复古精装本", "https://www.paperblanks.com/collections/planners", "", 800),
    ("Bodum 法压壶", "水杯", "经典法式咖啡压壶", "https://www.bodum.com/us/en/french-press", "", 700),
    ("Diptyque 限定礼盒", "创意礼盒", "法国香氛蜡烛礼品套装", "https://www.diptyqueparis.com/en/gifts/", "", 4972),
    ("Godiva 中秋巧克力", "中秋礼盒", "比利时巧克力中秋限定", "https://www.godiva.com/", "https://www.godiva.com/cdn/shop/files/39086_godiva-logo-svg.svg?v=1759343745&amp;width=1000", 1745),
    ("A.P.C. 纯棉T恤", "T恤", "法国A.P.C.纯棉Basic T恤", "https://www.apc.fr/categories/men/t-shirts", "", 4173),
    ("CASETiFY 防摔Ultra", "手机壳", "CASETiFY Impact极黑防摔手机壳", "https://www.casetify.com/category/iphone-17-pro-max-cases", "", 1430),
    ("Fellowes Eames 桌垫", "创意桌搭", "办公桌大型皮质桌垫", "https://www.fellowes.com/", "/_layouts/15/images/fgimg.png?rev=43", 3952),
    ("Nomad 真皮手机壳", "手机壳", "美国植鞣革手机壳", "https://www.nomadgoods.com/collections/cases", "https://cdn.shopify.com/s/files/1/0384/6721/files/apple-watch-natural-metal-band-front.jpg?v=1728060667&amp;width=1280&amp;height=630", 1200),
    ("Nalgene 经典水壶", "钥匙扣水壶", "BPA-Free经典户外水壶", "https://nalgene.com/product/32oz-wide-mouth-sustain/", "https://nalgene.com/wp-content/uploads/2025/12/nalgene-water-bottles.jpg", 800),
    ("Patagonia Torrentshell", "冲锋衣", "环保户外冲锋衣", "https://www.patagonia.com/product/mens-torrentshell-3l-rain-jacket/85241.html", "https://www.patagonia.com/dw/image/v2/BDJB_PRD/on/demandware.static/-/Sites-patagonia-master/default/dw7138ee44/images/hi-res/85241_GEMG.jpg?sw=256&amp;sh=256&amp;sfrm=png&amp;q=95&amp;bgcolor=f3f4ef", 1800),
    ("James Turrell 天窗装置", "装置艺术", "光与空间大师的Skyspace", "https://jamesturrell.com/", "", 1331),
    ("Vitamix 破壁机", "创意厨具", "美国Vitamix专业破壁料理机", "https://www.vitamix.com/us/en_us/venturist-series/", "", 4381),
    ("Stüssy 世界巡游T恤", "T恤", "Stüssy经典World Tour印花T恤", "https://www.stussy.com/collections/t-shirts", "", 3780),
    ("Anker 能量棒充电宝", "充电宝", "Anker PowerCore超薄充电宝", "https://www.anker.com/collections/power-banks", "https://cdn.shopify.com/s/files/1/0493/9834/9974/collections/Portable_Power.jpg?v=1625458091", 3628),
    ("Grovemade 实木显示器架", "创意桌搭", "俄勒冈实木胡桃木显示器架", "https://grovemade.com/shop/desk-accessories/", "", 4087),
    ("SMEG 多士炉", "创意厨具", "复古美学多士炉", "https://www.smeg.com/toasters", "https://www.smeg.com/binaries/content/gallery/smeg/categories/sda_smeg_frontale_tsf.jpg/sda_smeg_frontale_tsf.jpg/brx%3ApostcardDeskLarge", 1800),
    ("Le Creuset 珐琅马克杯", "水杯", "法式彩色珐琅马克杯", "https://www.lecreuset.com/coffee-and-tea/mugs-cups/", "", 1200),
    ("Mophie Powerstation", "充电宝", "苹果认证充电宝", "https://www.mophie.com/collections/portable-power", "", 800),
    ("Mammut 艾格极限冲锋衣", "冲锋衣", "瑞士专业户外冲锋衣", "https://www.mammut.com/int/en/cat/230-hardshell-jackets-men/", "https://images.ctfassets.net/l595fda2nfqd/493aXEg31Defo62SW4Wtk5/4e0f3fbf01a21bf774773e3e11094cda/hiking_ducan-spine_rgb_03895.jpg?fm=jpg&amp;w=512&amp;q=80", 1500),
    ("Stüssy 棒球帽", "帽子", "美式街头棒球帽", "https://www.stussy.com/collections/headwear", "http://www.stussy.com/cdn/shop/files/checkout-logo_256x256_c8c5b294-3bd0-4d8e-a5bd-e4066efcc662.png?v=1678808251", 1800),
    ("Native Union 编织充电宝", "充电宝", "编织线缆无线充电宝", "https://www.nativeunion.com/collections/power", "", 600),
    ("Jo Malone 圣诞礼盒", "创意礼盒", "祖玛珑限定圣诞礼盒", "https://www.jomalone.com/gifts", "", 1987),
    ("Maison Margiela 香氛礼盒", "创意礼盒", "Replica香水礼品套装", "https://www.maisonmargiela-fragrances.com/us/gifts", "", 3658),
    ("Essentials 连帽卫衣", "卫衣", "Fear of God ESSENTIALS经典连帽卫衣", "https://fearofgod.com/collections/essentials", "", 2106),
    ("Polo Ralph Lauren 棒球帽", "帽子", "Ralph Lauren经典刺绣棒球帽", "https://www.ralphlauren.com/men-accessories-hats-headwear/", "", 2024),
    ("Fjällräven 尼龙卡包", "卡包", "瑞典北极狐经典尼龙短钱包", "https://www.fjallraven.com/us/en-us/bags-gear/wallets/", "", 985),
    ("德龙 ECAM 咖啡机", "创意厨具", "意式全自动咖啡机", "https://www.delonghi.com/en-us/coffee/coffee-machines/automatic-coffee-machines/", "", 1500),
    ("Hydro Flask 宽口水壶", "钥匙扣水壶", "双层真空不锈钢水壶", "https://www.hydroflask.com/wide-mouth-with-flex-cap-32", "", 1200),
    ("Hobonichi 手帐", "日历", "日本经典手帐本", "https://www.1101.com/store/techo/en/", "https://www.1101.com/store/techo/2026/images/og/techo2026_en.jpg", 1500),
    ("MUJI 收纳盒", "收纳包", "极简收纳系列", "https://www.muji.com/jp/ja/store/cmdty/section/S107010101", "", 600),
    ("The North Face Summit", "冲锋衣", "巅峰系列专业冲锋衣", "https://www.thenorthface.com/en-us/explore/summit-series", "", 2200),
    ("IKEA SKADIS 收纳板", "收纳包", "模块化桌面收纳板", "https://www.ikea.com/us/en/cat/skadis-series-37813/", "https://www.ikea.com/global/assets/range-categorisation/images/skadis-series-37813.jpeg", 900),
    ("Palace 5-Panel 帽", "帽子", "英国滑板品牌帽子", "https://www.palaceskateboards.com/", "", 1400),
    ("Anish Kapoor 镜面装置", "装置艺术", "英国雕塑家巨型镜面不锈钢装置", "https://www.anishkapoor.com/", "", 3961),
    ("Daniel Arsham 侵蚀装置", "装置艺术", "未来考古学侵蚀石膏装置", "https://www.danielarsham.com/", "http://static1.squarespace.com/static/596e2ce46b8f5b88b9f39254/t/642cb55dae6e4d399558b1c2/1680651613945/AASoloLogoAsset+1.png?format=1500w", 3588),
    ("JR 巨型摄影装置", "装置艺术", "法国街头艺术家巨型摄影贴装置", "https://www.jr-art.net/", "/fbshare.jpg", 3421),
    ("Champion Reverse Weave", "卫衣", "Champion经典Reverse Weave圆领卫衣", "https://www.champion.com/collections/reverse-weave", "http://www.champion.com/cdn/shop/files/1200x628-1.jpg?v=1770045447&width=1024", 4791),
    ("Noah NY 十字徽标T恤", "T恤", "Noah NYC十字LogoT恤", "https://www.noahny.com/collections/tees", "", 4920),
    ("Stüssy Stock 5-Panel", "帽子", "Stüssy 5-Panel网面运动帽", "https://www.stussy.com/collections/headwear", "http://www.stussy.com/cdn/shop/files/checkout-logo_256x256_c8c5b294-3bd0-4d8e-a5bd-e4066efcc662.png?v=1678808251", 4335),
    ("ACW* 编织帽", "帽子", "A-COLD-WALL*工业风编织帽", "https://www.acoldwall.com/collections/headwear", "", 3264),
    ("DBrand Grip 手机壳", "手机壳", "DBrand Grip超薄防摔手机壳", "https://dbrand.com/shop/grip/cases/iphone", "", 1571),
    ("Mismo 皮质卡包", "卡包", "瑞典Mismo简洁牛皮卡包", "https://www.mismo.dk/products/card-holder", "", 942),
    ("Mountain Hardwear Ghost", "冲锋衣", "超轻羽绒冲锋衣", "https://www.mountainhardwear.com/c/mens-jackets/", "", 1100),
    ("Riedel 水晶酒杯", "水杯", "奥地利手工水晶酒杯", "https://www.riedel.com/en-us/shop/wine-glasses", "https://img.riedel.com/w_1200,h_600,q_80,v_dde8f4,hash_af8e84/dam/4000x2100px-Header-Site-n-XXL-Teaser-n-Hero-Product-Teaser-n-Related-Products-Teaser/RIEDEL/2022/2022-Genussletter-November_Fankhauser/4000x2100px_LIA_8271_special-usage-only.jpg", 1300),
    ("Wedgwood 骨瓷茶杯", "水杯", "英式骨瓷经典设计", "https://www.wedgwood.com/en-us/dining/drinkware/teacups-saucers/", "", 900),
    ("Pela 环保手机壳", "手机壳", "加拿大环保可降解手机壳", "https://www.pela.com/collections/phone-cases", "", 2231),
]

# 小红书 (33 items)
XIAOHONGSHU = [
    ("MOREOVER 北欧水杯", "水杯", "北欧风陶瓷水杯设计", "https://moreover.cc", "", 800),
    ("野兽派 花盒套装", "创意礼盒", "野兽派永生花礼盒", "https://www.thebeastshop.com/", "https://img.thebeastshop.com/static/images/bst-new-logo.png", 598),
    ("故宫文创 新年礼盒", "创意礼盒", "紫禁城新年限定礼盒", "https://www.dpm.org.cn/", "https://img.dpm.org.cn/static/themes_wap/image/wechat_share1.png", 2894),
    ("ROARINGWILD 卫衣", "卫衣", "国潮卫衣代表品牌", "https://www.roaringwild.com/", "http://roaringwild.com/cdn/shop/files/ROARINGWILD_NEW_Logo_WH_1920_1080_1200x1200.jpg?v=1749110173", 1500),
    ("故宫日历 2025", "日历", "故宫博物院经典日历", "https://www.dpm.org.cn/", "https://img.dpm.org.cn/static/themes_wap/image/wechat_share1.png", 4500),
    ("乐歌 E5 升降桌", "创意桌搭", "国货电动升降桌", "https://www.loctek.com/", "", 1600),
    ("气味图书馆 礼盒", "创意礼盒", "气味图书馆城市系列礼盒", "https://www.scenllab.com/", "", 2415),
    ("故宫端午礼盒", "端午礼盒", "故宫博物院端午文创礼盒", "https://www.dpm.org.cn/", "https://img.dpm.org.cn/static/themes_wap/image/wechat_share1.png", 1098),
    ("TOMTOMMY 卡包", "卡包", "极简设计卡包", "https://www.tomtommmy.com/", "", 500),
    ("几光 智能灯", "氛围灯", "国货智能氛围灯设计", "https://ezvalo.com/", "", 1100),
    ("泡泡玛特 潮玩礼盒", "创意礼盒", "Molly限定盲盒礼盒套装", "https://www.popmart.com/", "", 1156),
    ("元祖 雪月饼礼盒", "中秋礼盒", "元祖经典冰淇淋月饼礼盒", "https://www.ganso.com/", "", 4528),
    ("杏花楼 粽意礼盒", "端午礼盒", "上海老字号端午礼盒", "https://www.xinghualou.com/", "", 4893),
    ("豆瓣电影日历", "日历", "豆瓣经典电影日历", "https://www.douban.com/", "", 3200),
    ("美心 流心奶黄月饼", "中秋礼盒", "香港经典流心奶黄月饼礼盒", "https://www.maxims.com.hk/", "https://www.maxims.com.hk/media/logo/maxims_og_favicon.png", 1941),
    ("国家地理 光影装置", "装置艺术", "国家地理影像沉浸装置展", "https://www.nationalgeographic.com/", "https://assets-cdn.nationalgeographic.com/natgeo/static/default.NG.logo.dark.jpg", 1957),
    ("余德耀美术馆 装置展", "装置艺术", "上海余德耀美术馆装置艺术展", "https://www.yuzmshanghai.org/", "", 4999),
    ("敦煌日历 2025", "日历", "敦煌壁画主题日历", "https://www.dunhuang.com/", "", 3000),
    ("摩飞 多功能料理锅", "创意厨具", "网红多功能料理锅", "https://www.morphyrichards.com/", "http://morphyrichards.com/cdn/shop/files/Social_Image.jpg?v=1700278803", 2800),
    ("INXX 联名T恤", "T恤", "国潮设计师联名T恤", "https://www.inxx.com/", "", 1000),
    ("故宫文创茶杯", "水杯", "故宫联名茶具设计", "https://www.dpm.org.cn/", "https://img.dpm.org.cn/static/themes_wap/image/wechat_share1.png", 2100),
    ("野兽派联名水杯", "水杯", "野兽派与艺术家联名杯具", "https://www.thebeastshop.com/", "", 1500),
    ("北鼎 养生壶", "创意厨具", "养生壶品类第一", "https://www.buydeem.com/", "", 1900),
    ("国誉自我手帐", "日历", "日本时间管理手帐本", "https://www.kokuyo.com/en/", "/sites/default/files/shared_contents/wp-content/uploads/2021/10/bnr_jibuntecho_211001.jpg", 1200),
    ("奈雪の茶 中秋联名", "中秋礼盒", "奈雪中秋设计师联名礼盒", "https://www.naixue.com/", "", 3037),
    ("诸老大 端午礼盒", "端午礼盒", "经典江南粽子礼盒", "https://www.zgld.com/", "", 3643),
    ("UCCA 北京 装置展览", "装置艺术", "UCCA尤伦斯当代艺术中心装置展", "https://www.ucca.org.cn/", "https://www.ucca.org.cn/storage/public/images/3/ha68fe-23f066-25d07f.200.png", 3570),
    ("稻香村 月饼礼盒", "中秋礼盒", "百年老字号中秋月饼礼盒", "https://www.daoxiangcun.com/", "", 4512),
    ("泡泡玛特联名保温杯", "水杯", "盲盒IP跨界保温杯", "https://www.popmart.com/", "", 1800),
    ("Yeelight 氛围灯", "氛围灯", "小米生态智能灯带", "https://www.yeelight.com/", "", 900),
    ("单向历", "日历", "单向空间经典日历", "https://www.owspace.com/", "", 1800),
    ("BAGGU 环保购物袋", "收纳包", "彩色尼龙环保收纳袋", "https://www.baggu.com/collections/standard-baggu", "https://cdn.sanity.io/images/t9jjg1v5/production/2b1638c7fbe8a9ab35a51af7e16edd972c3f5fbd-1200x630.png", 2400),
    ("五芳斋 粽子礼盒", "端午礼盒", "中华老字号粽子礼盒", "https://www.wufangzhai.com/", "/uploads/image/20240902/1725255644274148.png", 2492),
]

# 抖音 (29 items)
DOUYIN = [
    ("小米 床头灯", "氛围灯", "高性价比智能床头灯", "https://www.mi.com/", "", 800),
    ("小米 口袋充电宝", "充电宝", "高性价比口袋充电宝", "https://www.mi.com/", "", 1200),
    ("Contigo 旅行杯", "水杯", "美国Contigo一键开盖旅行杯", "https://www.gocontigo.com/", "", 2499),
    ("Baseus Blade 薄版", "充电宝", "Baseus Blade笔记本超薄充电宝", "https://www.baseus.com/collections/power-banks", "http://www.baseus.com/cdn/shop/collections/Baseus_Elf_Power_Bank_65W_20000mAh_1_front_side_700x_65bd1d66-3ba4-4b64-a8c7-3b0d52204a14.webp?v=1677744576", 1238),
    ("Anker 收纳包", "收纳包", "数码线材收纳包", "https://www.anker.com/collections/all-accessories", "", 400),
    ("驼峰 运动水壶", "钥匙扣水壶", "专业运动补水壶", "https://www.camelbak.com/recreation/bottles", "", 500),
    ("罗马仕 充电宝", "充电宝", "国民充电宝品牌", "https://www.romoss.com/", "", 800),
    ("WASSUP T恤", "T恤", "国潮基础款T恤", "https://www.wassup.com/", "", 500),
    ("Nike Dri-FIT 运动帽", "帽子", "速干运动帽", "https://www.nike.com/w/hats-and-headwear-9zy6f", "https://www.nike.com/android-icon-192x192.png", 600),
    ("观夏 蜡烛礼盒", "创意礼盒", "东方植物香薰礼盒", "https://www.loeweperfumes.com/", "", 3114),
    ("上海 制造之外装置展", "装置艺术", "WAVELENGTH制造之外艺术装置群", "https://www.wavelength.com/", "https://assets.asana.biz/m/5a2dff1f176becc3/webimage-asana-share-image-logo.jpg", 4843),
    ("Helly Hansen Verglas", "冲锋衣", "Helly Hansen Verglas防水冲锋衣", "https://www.hellyhansen.com/en_us/mens-outerwear-jackets", "", 3235),
    ("FMACM 卫衣", "卫衣", "国潮设计感卫衣", "https://www.fmacm.com/", "", 700),
    ("凯乐石 冲锋衣", "冲锋衣", "国货专业登山冲锋衣", "https://www.kailas.com/", "", 900),
    ("Nalgene 运动水壶", "钥匙扣水壶", "户外运动经典水壶", "https://nalgene.com/product/32oz-wide-mouth-sustain/", "https://nalgene.com/wp-content/uploads/2025/12/nalgene-water-bottles.jpg", 600),
    ("广州酒家 端午礼盒", "端午礼盒", "广式粽子礼盒", "https://www.gzjj.com/", "img.sedoparking.com/images/js_preloader.gif", 3563),
    ("成都 时空魔方装置", "装置艺术", "沉浸式光影时空装置展", "https://www.timespacecube.com/", "", 4208),
    ("双立人 刀具套装", "创意厨具", "德国厨刀标杆", "https://www.zwilling.com/us/cutlery/knives/", "", 700),
    ("BEASTER 鬼脸T恤", "T恤", "国潮鬼脸印花T恤", "https://www.beaster.com/", "", 1200),
    ("华为智选 台灯", "氛围灯", "华为智选护眼台灯", "https://www.huawei.com/", "https://www-file.huawei.com/-/media/corp/home/image/logo_400x200.png", 500),
    ("BOTTLED JOY 吨吨桶", "水杯", "网红大容量运动水壶", "https://bottledjoy.com/", "http://bottledjoy.com/cdn/shop/files/5b6u5L_h5Zu_54mHXzIwMjMwNjEzMTY0NTMzLnBuZw.png?v=1686880714", 1800),
    ("乐纯 中秋酸奶礼盒", "中秋礼盒", "乐纯限定中秋酸奶礼盒", "https://www.lechun.com/", "", 1221),
    ("Govee 灯带套装", "氛围灯", "Govee智能RGBIC LED灯带", "https://www.govee.com/collections/led-strip-lights", "https://cdn.shopify.com/s/files/1/0512/3489/8105/files/Shipping_VI.png?v=1737431254&amp;width=100&amp;crop=center", 1120),
    ("SHARGE 闪极 Retro 67", "充电宝", "SHARGE机甲风透明充电宝", "https://www.sharge.com/products/retro-67", "http://sharge.com/cdn/shop/files/Retro67GaNCharger_4c90d722-1258-487c-b9e3-e158de744150.png?v=1772714414", 2988),
    ("MLB 经典帽款", "帽子", "MLB韩版时尚帽子", "https://www.mlbbrand.com/", "", 2500),
    ("倍思 氮化镓充电宝", "充电宝", "大容量快充充电宝", "https://www.baseus.com/collections/power-banks", "http://www.baseus.com/cdn/shop/collections/Baseus_Elf_Power_Bank_65W_20000mAh_1_front_side_700x_65bd1d66-3ba4-4b64-a8c7-3b0d52204a14.webp?v=1677744576", 700),
    ("三顿半 咖啡礼盒", "创意礼盒", "精品速溶咖啡礼盒套装", "https://www.saturnbird.com/", "", 4883),
    ("永璞 咖啡联名礼盒", "创意礼盒", "永璞咖啡设计师联名套装", "https://www.yongpu.com/", "", 3673),
    ("知味观 端午礼盒", "端午礼盒", "杭州老字号端午礼盒", "https://www.zhiweiguan.com/", "", 3667),
]

# Pinterest (2 items)
PINTEREST = [
    ("Pinterest 包装设计灵感", "创意礼盒", "全球包装设计创意集锦", "https://www.pinterest.com/categories/packaging/", "", 509),
    ("Pinterest 极简家居灵感", "创意礼盒", "极简北欧家居设计灵感集", "https://www.pinterest.com/categories/home/", "", 1696),
]

# Behance (1 items)
BEHANCE = [
    ("Behance UI/UX 精选合集", "创意礼盒", "Behance全球精选UI/UX设计案例", "https://www.behance.net/galleries/ui-ux", "", 2436),
]


def main():
    all_data = []
    for t in GOOD_DESIGN: all_data.append((*t, "Good Design Award"))
    for t in IF_DESIGN: all_data.append((*t, "iF设计奖"))
    for t in RED_DOT: all_data.append((*t, "Red Dot"))
    for t in A_DESIGN: all_data.append((*t, "A' Design Award"))
    for t in INSTAGRAM: all_data.append((*t, "Instagram"))
    for t in XIAOHONGSHU: all_data.append((*t, "小红书"))
    for t in DOUYIN: all_data.append((*t, "抖音"))
    for t in PINTEREST: all_data.append((*t, "Pinterest"))
    for t in BEHANCE: all_data.append((*t, "Behance"))

    items = []
    for title, cat, desc, url, image, likes, source in all_data:
        score_base = 8.0 if ("奖" in source or "Award" in source or source == "Pinterest" or source == "Behance") else 7.2
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
