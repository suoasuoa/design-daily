#!/usr/bin/env python3
"""Daily Design Digest Server - serves HTML + JSON data"""
import json, os, http.server, urllib.parse
from datetime import datetime

DIR = os.path.dirname(os.path.abspath(__file__))

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        
        # API endpoint for data
        if parsed.path == '/api/digest':
            data_path = os.path.join(DIR, 'data', 'latest.json')
            if os.path.exists(data_path):
                with open(data_path, 'r', encoding='utf-8') as f:
                    data = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(data.encode('utf-8'))
            else:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"items":[],"stats":{"total":0}}')
            return
        
        # Refresh trigger
        elif parsed.path == '/api/refresh':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status":"refresh manually: python3 scrape.py"}')
            return
        
        # Serve index.html
        elif parsed.path == '/' or parsed.path == '/index.html':
            self.path = '/index.html'
        
        # Everything else - serve from current dir
        return super().do_GET()
    
    def log_message(self, format, *args):
        if len(args) >= 3:
            print(f'[{datetime.now().strftime("%H:%M:%S")}] {args[0]} {args[1]} {args[2]}')
        elif len(args) >= 1:
            print(f'[{datetime.now().strftime("%H:%M:%S")}] {" ".join(str(a) for a in args)}')

if __name__ == '__main__':
    port = 3456
    os.chdir(DIR)
    print(f'\n  Daily Design Digest Server')
    print(f'  http://localhost:{port}')
    print(f'  Press Ctrl+C to stop\n')
    httpd = http.server.HTTPServer(('127.0.0.1', port), Handler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('\nServer stopped')
