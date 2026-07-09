#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YS89 儀表板本地伺服器
靜態檔案服務（取代 python -m http.server）+ GA4 自訂日期查詢端點
用法：python dashboard_server.py [port]  (預設 8765)
"""
import json, os, sys, urllib.parse, io
from http.server import HTTPServer, SimpleHTTPRequestHandler

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)


class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/api/ga4-custom':
            self._handle_ga4_custom(parsed.query)
        else:
            super().do_GET()

    def _handle_ga4_custom(self, query):
        params = urllib.parse.parse_qs(query)
        start = params.get('start', [None])[0]
        end   = params.get('end',   [None])[0]

        if not start or not end:
            return self._json_error(400, '缺少 start 或 end 日期參數')

        try:
            from ga4_fetch import get_ga4_client, fetch_custom_range_data
            print(f'[GA4] 自訂查詢 {start} ~ {end} ...')
            client = get_ga4_client()
            data   = fetch_custom_range_data(client, start, end)
            body   = json.dumps(data, ensure_ascii=False).encode('utf-8')
            print(f'[GA4] 完成 sessions={data["kpis"].get("sessions", "?")}')

            self.send_response(200)
            self.send_header('Content-Type',  'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(body)

        except Exception as e:
            import traceback; traceback.print_exc()
            self._json_error(500, str(e))

    def _json_error(self, code, msg):
        body = json.dumps({'error': msg}, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type',  'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass  # 關掉每次請求的 access log


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    server = HTTPServer(('', port), DashboardHandler)
    print(f'✅ YS89 儀表板：http://localhost:{port}')
    print(f'   自訂 GA4 查詢：/api/ga4-custom?start=YYYY-MM-DD&end=YYYY-MM-DD')
    server.serve_forever()
