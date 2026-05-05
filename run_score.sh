#!/bin/bash
cd /tmp/design-daily
python3 accumulate.py
python3 generate.py
git add -A
git commit -m "✨ accumulate: 新增选品评分模块（5维评分/总分<35过滤）"
git push
