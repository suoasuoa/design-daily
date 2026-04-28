#!/bin/bash
# 🎨 Daily Design Digest - 一键启动
# Usage: bash ~/.openclaw/workspace/design-daily/complete.sh

cd ~/.openclaw/workspace/design-daily

echo "🎨 Daily Design Digest"
echo "━━━━━━━━━━━━━━━━━━━━━━"

# 1. Start the local server
echo "🚀 Starting server on http://localhost:3456"
node server.js &

sleep 1

# 2. Open in browser
open http://localhost:3456

echo "✅ Dashboard is opening in your browser"
echo ""
echo "📌 手动添加内容:"
echo "  打开 daily-data.json，编辑后保存，刷新页面即可"
