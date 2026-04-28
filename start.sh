#!/bin/bash
echo ""
echo "  Daily Design Digest"
echo "  =================="
echo ""
cd "$(dirname "$0")"
echo " 1. Scraping design content from 4 platforms × 7 categories..."
echo "    (This takes 2-3 minutes first time)"
python3 scrape_full.py 2>&1 | sed 's/^/    /'
echo ""
echo " 2. Starting server..."
echo "    Open: http://localhost:3456"
echo "    Press Ctrl+C to stop"
echo ""
python3 server.py
