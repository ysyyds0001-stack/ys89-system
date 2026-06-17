"""YS89 Social Bot - Pixnet 發文 (Playwright JODIT 編輯器自動化)
流程: 登入 → panel.pixnet.tw → 寫文章 → 發布
"""
import asyncio, json, os, sys
from playwright.async_api import async_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

def load_keys():
    with open(os.path.join(BASE_DIR, "api_keys.json"), encoding="utf-8") as f:
        return json.load(f)

async def _fill_react(page, selector, value):
    el = page.locator(selector)
    await el.click()
    await el.press("Control+a")
    await el.press("Delete")
    await page.keyboard.type(value, delay=30)

async def _post(title, content, tags=None):
    keys = load_keys()
    pk       = keys.get("pixnet", {})
    email    = pk.get("email", "")
    password = pk.get("password", "")
    username = pk.get("username", "oldkplaynotes")

    if not email or not password:
        raise ValueError("請先在 api_keys.json 填入 pixnet.email 和 pixnet.password")

    AUTH_URL = (f"https://{username}.pixnet.net/auth/authorize"
                f"?redirect_uri=https%3A%2F%2F{username}.pixnet.net%2Fblog")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        ctx = await browser.new_context(
            user_agent=UA, locale="zh-TW",
            viewport={"width": 1280, "height": 900}
        )
        await ctx.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
        )
        page = await ctx.new_page()

        # ── 1. 登入 ─────────────────────────────────────────────
        await page.goto(AUTH_URL, timeout=60000, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)
        if "login" in page.url or "account.pixnet" in page.url:
            await _fill_react(page, 'input[name="username"]', email)
            await _fill_react(page, 'input[name="password"]', password)
            await page.click('button[type="submit"]')
            await page.wait_for_timeout(6000)
        if "login" in page.url:
            raise RuntimeError(f"Pixnet 登入失敗: {page.url}")

        # ── 2. 前往 panel 的文章頁 ─────────────────────────────
        await page.goto("https://panel.pixnet.tw/", timeout=60000, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        await page.locator('a[href="/posts"]').click()
        await page.wait_for_timeout(3000)
        await page.locator('a[href="/posts/create"]').click()
        await page.wait_for_timeout(4000)

        # ── 3. 建立草稿（開始寫文章）─────────────────────────────
        # 偶發 500，最多重試 3 次
        for attempt in range(3):
            start_btn = page.locator('button:has-text("開始寫")')
            await start_btn.first.click()
            try:
                await page.wait_for_url(
                    lambda url: "/posts/" in url and url.split("/posts/")[-1].isdigit(),
                    timeout=25000
                )
                break  # 成功，跳出重試
            except Exception:
                if attempt == 2:
                    raise
                # 回到建立頁重試
                await page.goto("https://panel.pixnet.tw/posts/create", timeout=30000, wait_until="domcontentloaded")
                await page.wait_for_timeout(4000)
        await page.wait_for_timeout(3000)
        post_id = page.url.rstrip("/").split("/")[-1]
        print(f"草稿 ID: {post_id}, URL: {page.url}")

        # ── 4. 填文章標題 ───────────────────────────────────────
        # 等待 JODIT 編輯器載入
        await page.wait_for_selector('.jodit-wysiwyg, [contenteditable="true"]', timeout=20000)
        await page.wait_for_timeout(2500)
        # 用 get_by_placeholder 找標題欄（避免 CSS 中文選擇器在 Windows 編碼壞掉）
        title_el = page.get_by_placeholder("請輸入文章標題")
        await title_el.wait_for(timeout=10000)
        await title_el.click()
        await page.keyboard.press("Control+a")
        await page.keyboard.press("Delete")
        await page.keyboard.type(title, delay=40)
        await page.wait_for_timeout(800)

        # ── 5. 填 JODIT 編輯器內容 ──────────────────────────────
        jodit = page.locator('.jodit-wysiwyg[contenteditable="true"]').first
        if await jodit.count() == 0:
            jodit = page.locator('div[contenteditable="true"]').first
        await jodit.click()
        await page.evaluate("""(html) => {
            const ed = document.querySelector('.jodit-wysiwyg[contenteditable="true"]')
                    || document.querySelector('div[contenteditable="true"]');
            if (ed) { ed.innerHTML = html; ed.dispatchEvent(new Event('input', {bubbles:true})); }
        }""", content)
        await page.wait_for_timeout(1500)

        # ── 6. 填標籤 ────────────────────────────────────────────
        if tags:
            tag_input = page.locator('input[placeholder*="標籤"], input[placeholder*="tag"]')
            if await tag_input.count() > 0:
                for tag in tags:
                    await tag_input.first.fill(tag)
                    await tag_input.first.press("Enter")
                    await page.wait_for_timeout(300)

        # ── 6.5 設定閱讀權限為公開（在發布前） ───────────────────
        # 右側面板往下捲動，顯示「文章閱讀權限」combobox
        await page.evaluate("""() => {
            document.querySelectorAll('*').forEach(el => {
                const s = window.getComputedStyle(el);
                if (el.scrollHeight > el.clientHeight + 50 &&
                    (s.overflowY === 'auto' || s.overflowY === 'scroll')) {
                    el.scrollTop = 999;
                }
            });
        }""")
        await page.wait_for_timeout(600)
        # 點開「文章閱讀權限」combobox button
        clicked = await page.evaluate("""() => {
            const label = Array.from(document.querySelectorAll('*'))
                .find(el => el.innerText?.trim() === '\\u6587\\u7ae0\\u95b1\\u8b80\\u6b0a\\u9650' && el.children.length < 4);
            if (!label) return 'label not found';
            const btn = label.parentElement?.querySelector('button[role=combobox]');
            if (!btn) return 'btn not found';
            btn.click();
            return 'opened: ' + btn.innerText.trim();
        }""")
        print(f"[visibility combobox] {clicked}")
        await page.wait_for_timeout(500)
        # 選「公開」option
        opted = await page.evaluate("""() => {
            const opts = Array.from(document.querySelectorAll('[role=option]'));
            const pub = opts.find(o => o.innerText?.trim() === '\\u516c\\u958b');
            if (pub) { pub.click(); return 'selected: ' + pub.innerText.trim(); }
            return 'option not found, total=' + opts.length;
        }""")
        print(f"[visibility option] {opted}")
        await page.wait_for_timeout(600)

        # ── 7. 發布 ──────────────────────────────────────────────
        # 等 JODIT 自動儲存
        await page.wait_for_timeout(2000)
        all_btns = page.locator('button:has-text("發布")')
        for i in range(await all_btns.count()):
            txt = (await all_btns.nth(i).inner_text()).strip()
            if "草稿" not in txt:
                await all_btns.nth(i).click()
                break
        await page.wait_for_timeout(2000)
        confirm_btn = page.locator('button:has-text("確定"), button:has-text("確認發布")')
        if await confirm_btn.count() > 0:
            await confirm_btn.first.click()
        await page.wait_for_timeout(3000)

        final_url = page.url
        # 取文章公開 URL
        post_url = f"https://{username}.pixnet.net/blog/posts/{post_id}"
        print(f"發文完成: {post_url}")
        await browser.close()

    return {"ok": True, "url": post_url, "id": post_id}


def post_article(title, content, tags=None):
    return asyncio.run(_post(title, content, tags))


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) < 2:
        print("用法: python pixnet_post.py '標題' '內容' [標籤1,標籤2]")
        sys.exit(1)
    t, c = args[0], args[1]
    tg = args[2].split(",") if len(args) > 2 else []
    r = post_article(t, c, tg)
    print(json.dumps(r, ensure_ascii=False))
