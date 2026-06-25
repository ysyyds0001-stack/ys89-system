import json, requests, datetime, sys

sys.stdout.reconfigure(encoding='utf-8')

TW    = datetime.timezone(datetime.timedelta(hours=8))
now   = datetime.datetime.now(TW)
today = now.strftime('%Y-%m-%d')
day3  = (now - datetime.timedelta(days=3)).strftime('%Y-%m-%d')
day7  = (now - datetime.timedelta(days=7)).strftime('%Y-%m-%d')

# ── 讀資料 ──────────────────────────────────────────────────────
with open('ga4-data.json', encoding='utf-8') as f:
    ga4 = json.load(f)

with open('social-feed.json', encoding='utf-8') as f:
    sf  = json.load(f)

kpis       = ga4.get('kpis', {})
kpis_7d    = ga4.get('kpis_7d', {})
kpis_prev  = ga4.get('kpis_prev7d', {})
accts_7d   = ga4.get('accounts_7d', [])
accts_prev = ga4.get('accounts_prev7d', [])
wr         = ga4.get('week_range', {})
updated    = ga4.get('lastUpdated', '')[:10]

# ── 工具函式 ─────────────────────────────────────────────────────
def arrow(cur, prev):
    if not prev or prev == 0:
        return ''
    diff = cur - prev
    pct  = diff / prev * 100
    if abs(pct) < 1:
        return '  →'
    return f'  ↑+{pct:.0f}%' if diff > 0 else f'  ↓{pct:.0f}%'

def fmt_posts(posts, limit=6):
    lines = []
    for p in posts[:limit]:
        imp   = p.get('impressions') or 0
        likes = p.get('likes') or 0
        name  = p.get('personaName') or p.get('persona') or '—'
        plat  = p.get('platform', '').upper()
        note  = p.get('note', '')
        line  = f"• {p['date']} <b>{name}</b> [{plat}]"
        if imp:   line += f"  曝光 {imp:,}"
        if likes: line += f"  ❤ {likes:,}"
        if note:  line += f"\n  └ {note}"
        lines.append(line)
    return lines

def fmt_accounts(accts, prev_accts=None):
    prev_map = {a['name']: a for a in (prev_accts or [])}
    lines = []
    for a in accts:
        name = a.get('name', '—')
        s    = a.get('s', 0)
        cta  = a.get('cta', 0)
        rate = f"{cta/s*100:.0f}%" if s else '—'
        prev = prev_map.get(name, {})
        chg  = arrow(s, prev.get('s', 0)) if prev else ''
        lines.append(f"• <b>{name}</b>  {s:,} sessions{chg} / CTA {cta:,} ({rate})")
    return lines

# ── 貼文資料 ────────────────────────────────────────────────────
all_posts = sf.get('posts', [])
posts_3d  = [p for p in all_posts if p.get('date','') >= day3 and (p.get('impressions') or p.get('likes'))]
posts_7d  = [p for p in all_posts if p.get('date','') >= day7 and (p.get('impressions') or p.get('likes'))]
posts_3d.sort(key=lambda x: (x.get('impressions') or 0), reverse=True)
posts_7d.sort(key=lambda x: (x.get('impressions') or 0), reverse=True)

# ── 組報告 ──────────────────────────────────────────────────────
lines = [
    f"📊 <b>YS89 每日成效報告</b>",
    f"📅 {today}  ·  台灣時間 09:00",
    "",
]

# 1. 近 3 天貼文曝光
if posts_3d:
    lines += [f"━━━ 近 3 天貼文曝光 ━━━"] + fmt_posts(posts_3d)
else:
    lines += ["━━━ 近 3 天貼文曝光 ━━━", "（尚無填入數字）"]

lines.append("")

# 2. 近一周貼文曝光（排除已在近3天出現的重複，取前 8）
lines += [f"━━━ 近一周貼文曝光 ━━━"]
if posts_7d:
    shown_urls = {p.get('postUrl') for p in posts_3d}
    extra = [p for p in posts_7d if p.get('postUrl') not in shown_urls]
    all_week = posts_3d + extra
    all_week.sort(key=lambda x: (x.get('impressions') or 0), reverse=True)
    lines += fmt_posts(all_week, limit=8)
    lines.append(f"（共 {len(posts_7d)} 篇有成效資料）")
else:
    lines.append("（尚無填入數字）")

lines.append("")

# 3. 本週 GA4 成效
tw_s   = kpis_7d.get('sessions', 0)
tw_u   = kpis_7d.get('activeUsers', 0)
tw_cta = kpis_7d.get('cta', 0)
tw_cvr = kpis_7d.get('conversionRate', 0)
pw_s   = kpis_prev.get('sessions', 0)
pw_u   = kpis_prev.get('activeUsers', 0)
pw_cta = kpis_prev.get('cta', 0)

wr_this = wr.get('this', '近 7 天')
lines += [
    f"━━━ 本週 GA4 成效（{wr_this}）━━━",
    f"👥 活躍用戶：<b>{tw_u:,}</b>{arrow(tw_u, pw_u)}",
    f"📈 工作階段：<b>{tw_s:,}</b>{arrow(tw_s, pw_s)}",
    f"🎯 CTA 點擊：<b>{tw_cta:,}</b>  轉換率 {tw_cvr:.1f}%{arrow(tw_cta, pw_cta)}",
    "",
    "帳號 Top 5：",
] + fmt_accounts(accts_7d, accts_prev)

lines.append("")

# 4. 上週 GA4 成效
wr_prev = wr.get('prev', '上週')
lines += [
    f"━━━ 上週 GA4 成效（{wr_prev}）━━━",
    f"👥 活躍用戶：{pw_u:,}",
    f"📈 工作階段：{pw_s:,}",
    f"🎯 CTA 點擊：{pw_cta:,}  轉換率 {kpis_prev.get('conversionRate',0):.1f}%",
    "",
    "帳號 Top 5：",
] + fmt_accounts(accts_prev)

lines.append("")

# 5. 累積成效（28 天）
active  = kpis.get('activeUsers', 0)
sess    = kpis.get('sessions', 0)
cta     = kpis.get('cta', 0)
conv    = kpis.get('conversionRate', 0)
accounts_28 = ga4.get('accounts', [])
top5 = sorted(accounts_28, key=lambda x: x.get('s', 0), reverse=True)[:5]

lines += [
    f"━━━ 累積成效（近 28 天，GA4 截至 {updated}）━━━",
    f"👥 活躍用戶：{active:,}",
    f"📈 工作階段：{sess:,}",
    f"🎯 CTA 點擊：{cta:,}  轉換率 {conv:.1f}%",
    "",
    "帳號累積 Top 5：",
] + fmt_accounts(top5)

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
