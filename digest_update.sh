#!/bin/bash
# Daily Design Digest — 每日定时更新脚本
# 由 launchctl 触发，每天 9:00 / 15:00 / 21:00 执行

export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
cd /Users/xuebao/.openclaw/workspace/design-daily || exit 1

echo "[$(date '+%Y-%m-%d %H:%M')] 开始更新..." >> /tmp/design-digest.log

/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 scrape.py >> /tmp/design-digest.log 2>&1

echo "[$(date '+%Y-%m-%d %H:%M')] 更新完成" >> /tmp/design-digest.log
