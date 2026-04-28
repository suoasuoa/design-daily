#!/bin/bash
# Daily Design Digest — 一键启动脚本
# 先跑爬虫，再启动服务器
cd "$(dirname "$0")"

echo '🎨 Daily Design Digest'
echo "📅 $(date '+%Y-%m-%d %H:%M')"
echo '━━━━━━━━━━━━━━━━━━━━━'

# 运行爬虫
echo '🔄 更新数据...'
python3 scrape.py

# 启动服务器
echo ''
echo '🚀 启动服务器 http://localhost:3456'
python3 server.py
