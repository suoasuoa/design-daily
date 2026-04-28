#!/usr/bin/env python3
"""
Daily Design Digest - 数据自动生成器
每天3次自动更新：Pinterest/Behance实时爬取 + 品牌精选数据
爬虫带重试机制 + 多重降级提取 + 随机User-Agent
"""
import json, os, random, datetime, re, sys, urllib.request, urllib.error, ssl, urllib.parse, time
from collections import Counter

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# ======================================================================
# 精选品牌产品数据（294条，精确URL + OG图片 + 来源归属）
# 不依赖任何在线API，离线可用
# ======================================================================
BRAND_ITEMS = []
