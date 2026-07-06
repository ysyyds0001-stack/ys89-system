# -*- coding: utf-8 -*-
"""
Threads 成效讀取伺服器
啟動: python threads_metrics.py
API:  GET http://localhost:5568/metrics?url=https://www.threads.com/@user/post/xxx
      GET http://localhost:5568/metrics?url=...&reply_handles=handle1,handle2
回傳: {"likes":0,"replies":0,"reposts":0,"shares":0,"views":0,"replyUrl":"..."}
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json, urllib.parse, sys

PORT = 5568

JS_EXTRACT = """() => {
    // 瀏覽數：頁面上最後一個含「次瀏覽」的葉節點（串文整體瀏覽數，通常在頁首）
    const viewEls = [...document.querySelectorAll('*')]
        .filter(e => e.children.length === 0 && e.textContent.includes('次瀏覽'));
    const viewEl = viewEls[0] || null;
    const viewRaw = viewEl ? viewEl.textContent.replace(/[^\\d.萬千百]/g,'') : '0';
    let views = 0;
    if (viewRaw.includes('萬')) {
        views = Math.round(parseFloat(viewRaw) * 10000);
    } else {
        views = parseInt(viewRaw.replace(/[^\\d]/g,'')) || 0;
    }

    // 找「最後一個」action bar：回覆頁面有多個帖，最後一個才是目標貼文
    // action bar = 同時含 讚/回覆/轉發/分享 的最小容器
    const allLikeLabels = [...document.querySelectorAll('*')]
        .filter(e => e.children.length === 0 && e.textContent.trim() === '讚');
    // 取最後一個 '讚' 找到的 actionBar（最下方的貼文）
    const likeLabel = allLikeLabels[allLikeLabels.length - 1] || null;
    let actionBar = likeLabel;
    for (let i = 0; i < 10 && actionBar; i++) {
        actionBar = actionBar.parentElement;
        const t = actionBar ? actionBar.textContent : '';
        if (['讚','回覆','轉發','分享'].filter(k => t.includes(k)).length >= 3) break;
    }

    // 在 action bar 範圍內，找標籤旁邊的數字（Threads 互動為 0 時不顯示數字 → 回傳 0）
    function getMetric(label) {
        if (!actionBar) return 0;
        const labelEl = [...actionBar.querySelectorAll('*')]
            .find(e => e.children.length === 0 && e.textContent.trim() === label);
        if (!labelEl) return 0;
        // 從標籤往上最多 3 層，在容器內找同層數字節點
        let container = labelEl;
        for (let i = 0; i < 4; i++) {
            container = container.parentElement;
            if (!container || !actionBar.contains(container)) break;
            const numEl = [...container.querySelectorAll('*')]
                .find(e => e.children.length === 0
                    && /^[\\d,.]+$/.test(e.textContent.trim())
                    && e !== labelEl);
            if (numEl) {
                const raw = numEl.textContent.trim().replace(/,/g,'');
                return raw.includes('萬') ? Math.round(parseFloat(raw)*10000) : (parseInt(raw)||0);
            }
        }
        return 0;  // 沒找到數字 = Threads 不顯示 = 真實 0
    }

    return {
        likes:   getMetric('讚'),
        replies: getMetric('回覆'),
        reposts: getMetric('轉發'),
        shares:  getMetric('分享'),
        views
    };
}"""

JS_FIND_REPLY = """(handles) => {
    const currentPostId = window.location.pathname.split('/post/')[1] || '';
    const links = [...document.querySelectorAll('a[href*="/post/"]')]
        .map(a => {
            const h = a.href || '';
            return h.startsWith('/') ? 'https://www.threads.com' + h : h;
        })
        .filter(h => h.includes('threads.com') && h.includes('/post/'));

    for (const handle of handles) {
        const found = links.find(href =>
            href.includes('/@' + handle + '/post/') &&
            !href.split('/post/')[1]?.startsWith(currentPostId)
        );
        if (found) return found.split('?')[0];
    }
    return null;
}"""


def scrape(url: str, reply_handles: list = None) -> dict:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise RuntimeError("Playwright 未安裝，請執行: pip install playwright && playwright install chromium")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(locale='zh-TW', user_agent=(
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/124.0.0.0 Safari/537.36'
        ))
        page = ctx.new_page()
        try:
            page.goto(url, wait_until='networkidle', timeout=25000)
            page.wait_for_timeout(2000)

            reply_url = None
            if reply_handles:
                # 捲動三次讓回覆載入
                for _ in range(3):
                    page.evaluate('window.scrollBy(0, 600)')
                    page.wait_for_timeout(800)
                reply_url = page.evaluate(JS_FIND_REPLY, reply_handles)
                if reply_url:
                    print(f"     ↩ 找到回覆: {reply_url}")
                    page.goto(reply_url, wait_until='networkidle', timeout=25000)
                    page.wait_for_timeout(1500)
                else:
                    print(f"     ⚠ 未找到回覆，讀取原文數據")

            result = page.evaluate(JS_EXTRACT)
            if reply_url:
                result['replyUrl'] = reply_url
        finally:
            browser.close()
    return result


class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/health':
            self._json({"ok": True})
            return
        if parsed.path == '/metrics':
            params = urllib.parse.parse_qs(parsed.query)
            url = params.get('url', [None])[0]
            if not url:
                self._json({"error": "missing url"}, 400)
                return
            reply_handles = []
            if params.get('reply_handles'):
                reply_handles = [h.strip() for h in params['reply_handles'][0].split(',') if h.strip()]
            print(f"  → 讀取: {url}")
            if reply_handles:
                print(f"     搜尋回覆角色: {reply_handles}")
            try:
                metrics = scrape(url, reply_handles or None)
                label = '(回覆)' if metrics.get('replyUrl') else '(主文)'
                print(f"     {label} likes={metrics['likes']} views={metrics['views']}")
                self._json(metrics)
            except Exception as e:
                print(f"     ❌ {e}")
                self._json({"error": str(e)}, 500)
            return
        self._json({"error": "not found"}, 404)

    def _json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self._cors()
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')

    def log_message(self, *args): pass


if __name__ == '__main__':
    print(f'✅ Threads 成效讀取伺服器已啟動 → http://localhost:{PORT}')
    print('   使用 Ctrl+C 停止\n')
    try:
        HTTPServer(('localhost', PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        print('\n已停止')
