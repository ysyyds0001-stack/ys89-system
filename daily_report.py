import json, requests, datetime, sys

sys.stdout.reconfigure(encoding='utf-8')

TW = datetime.timezone(datetime.timedelta(hours=8))
today = datetime.datetime.now(TW).strftime('%Y-%m-%d')
three_days_ago = (datetime.datetime.now(TW) - datetime.timedelta(days=3)).strftime('%Y-%m-%d')

# ── 讀資料 ──────────────────────────────────────────────────────
with open('ga4-data.json', encoding='utf-8') as f:
    ga4 = json.load(f)

with open('social-feed.json', encoding='utf-8') as f:
    sf  = json.load(f)

kpis     = ga4.get('kpis', {})
accounts = ga4.get('accounts', [])
updated  = ga4.get('lastUpdated', '')[:10]

# ── GA4 KPIs ────────────────────────────────────────────────────
active  = kpis.get('activeUsers', 0)
sess    = kpis.get('sessions', 0)
cta     = kpis.get('cta', 0)
conv    = kpis.get('conversionRate', 0)

# ── 各帳號 Top 5 ────────────────────────────────────────────────
top_accts = sorted(accounts, key=lambda x: x.get('s', 0), reverse=True)[:5]

# ── 近 3 天有曝光數的貼文 ───────────────────────────────────────
posts = sf.get('posts', [])
recent = [p for p in posts if p.get('date','') >= three_days_ago and (p.get('impressions') or p.get('likes'))]
recent.sort(key=lambda x: x.get('date',''), reverse=True)

# ── 組報告文字 ──────────────────────────────────────────────────
lines = [
    f"📊 <b>YS89 每日成效報告</b>",
    f"📅 {today}  ·  台灣時間 09:00",
    f"（GA4 資料截至 {updated}）",
    f"",
    f"━━━ 累積 GA4 成效 ━━━",
    f"👥 活躍用戶：<b>{active:,}</b>",
    f"📈 工作階段：<b>{sess:,}</b>",
    f"🎯 CTA 點擊：<b>{cta:,}</b>  轉換率 {conv:.1f}%",
    f"",
    f"━━━ 帳號成效 Top 5 ━━━",
]
for a in top_accts:
    name  = a.get('name','—')
    s_val = a.get('s', 0)
    c_val = a.get('cta', 0)
    rate  = f"{c_val/s_val*100:.0f}%" if s_val else '—'
    lines.append(f"• <b>{name}</b>  {s_val:,} sessions / CTA {c_val:,} ({rate})")

if recent:
    lines += ["", "━━━ 近 3 天貼文曝光 ━━━"]
    for p in recent[:6]:
        imp   = p.get('impressions') or 0
        likes = p.get('likes') or 0
        name  = p.get('personaName') or p.get('persona') or '—'
        plat  = p.get('platform','').upper()
        note  = p.get('note','')
        line  = f"• {p['date']} <b>{name}</b> [{plat}]"
        if imp:   line += f"  曝光 {imp:,}"
        if likes: line += f"  ❤ {likes:,}"
        if note:  line += f"\n  └ {note}"
        lines.append(line)
else:
    lines += ["", "近 3 天尚無填入曝光數字的貼文"]

lines += [
    "",
    "⚠️ <b>Threads / IG 洞察</b>請開 app 手動確認",
    "→ 回系統 GA4 頁「每日成效觀察」填入數字",
]

text = "\n".join(lines)

# ── 推送到 Mike Telegram Bot ─────────────────────────────────────
MIKE_TOKEN = '8795790357:AAGN9DBgcmlsV_sTs1697s_94X7uaxfLzvw'
MIKE_CHAT  = '8579100990'

r = requests.post(
    f'https://api.telegram.org/bot{MIKE_TOKEN}/sendMessage',
    json={
        'chat_id': MIKE_CHAT,
        'text': text,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True,
    },
    timeout=15
)
print(f'Telegram status: {r.status_code}')
if not r.ok:
    print(r.text)
    sys.exit(1)
