#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YS89 社群成效對外 API 產生器
從現有系統資料源組出機器可讀的 social-feed.json，給「YS89 SEO 成效儀表板」每日抓取。

資料源（皆為公開 HTTP，無需金鑰）:
  - 發文管理系統 Workers API: thread_activities(炒話題) + posts(發文追蹤)
  - UTM 產生器 D1: personas 主檔(code/name/agent)

輸出: social-feed.json (repo 根目錄) → GitHub Pages 公開
對接主鍵: utmContent (= 貼文連結上的 utm_content 參數)；沒帶 UTM 一律 null，不編造。
"""

import json
import sys
import urllib.request
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, parse_qs

# Windows 主控台可能是 cp950，強制 stdout/stderr 用 UTF-8 才能印 emoji/中文
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ═══════════════════════════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════════════════════════

SYS_API = "https://ys89-api.ysyyds0001.workers.dev/api"   # 發文管理系統資料
UTM_API = "https://ys89-utm.pages.dev/api"                # UTM 產生器人設主檔
OUTPUT_FILE = "social-feed.json"
DAYS_WINDOW = 90  # posts 至少涵蓋最近 90 天

# 平台正規化（輸出一律小寫）
PLATFORM_MAP = {
    "threads": "threads", "th": "threads",
    "ig": "ig", "instagram": "ig",
    "fb": "fb", "facebook": "fb",
    "line": "line",
}


def norm_platform(p):
    if not p:
        return None
    return PLATFORM_MAP.get(str(p).strip().lower(), str(p).strip().lower())


def fetch_json(url, retries=3):
    """抓 JSON，失敗重試。"""
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ys89-social-feed/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            last = e
    raise RuntimeError(f"抓取失敗 {url}: {last}")


def num_or_none(v):
    """轉 number；空字串/None/非數字 → None（0 保留，0 和『沒記錄』不同）。"""
    if v is None or v == "":
        return None
    try:
        n = float(v)
        return int(n) if n == int(n) else n
    except (TypeError, ValueError):
        return None


def parse_utm_content(post_url):
    """從貼文連結解析實際的 utm_content；沒有就回 None（不編造）。"""
    if not post_url:
        return None
    try:
        qs = parse_qs(urlparse(post_url).query)
        vals = qs.get("utm_content")
        return vals[0] if vals and vals[0] else None
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════
# 人設主檔：name → {code, agent}
# ═══════════════════════════════════════════════════════════════

def build_persona_index(master):
    """回傳 (name_to_code, name_to_agent, master_rows)。中文名 / code 都當查找鍵。"""
    name_to_code, name_to_agent = {}, {}
    for r in master:
        name = (r.get("name") or "").strip()
        code = (r.get("code") or "").strip() or None
        agent = (r.get("agent") or "").strip() or None
        if name:
            name_to_code[name] = code
            name_to_agent[name] = agent
        if code:
            name_to_code[code] = code
            name_to_agent[code] = agent
    return name_to_code, name_to_agent


def resolve_code(persona_name, name_to_code):
    """把貼文上的 personaName 對到 code：先精確，再包含（例『蟹蟹世足觀測站』→ crab）。"""
    if not persona_name:
        return None
    n = persona_name.strip()
    if n in name_to_code:
        return name_to_code[n]
    for master_name, code in name_to_code.items():
        if code and master_name and master_name in n:
            return code
    return None


# ═══════════════════════════════════════════════════════════════
# 組 posts
# ═══════════════════════════════════════════════════════════════

def from_thread_activities(rows, name_to_code):
    """炒話題追蹤 → 貼文（每平台一筆，指標取 platformMetrics）。"""
    out = []
    for a in rows:
        date = (a.get("date") or "")[:10]
        if not date:
            continue
        persona_name = a.get("personaName") or None
        code = resolve_code(persona_name, name_to_code)
        url = a.get("url") or None
        note = a.get("topic") or a.get("notes") or None
        pm = a.get("platformMetrics") or {}
        platforms = a.get("platforms") or list(pm.keys()) or ["Threads"]
        # utmContent：優先用系統記錄的欄位（炒話題新增時自動產生），再退而求其次解析連結
        utm = (a.get("utmContent") or "").strip() or parse_utm_content(url)
        for plat in platforms:
            m = pm.get(plat) or {}
            out.append({
                "date": date,
                "persona": code,
                "personaName": persona_name,
                "platform": norm_platform(plat),
                "postUrl": url,
                "utmContent": utm or None,
                "impressions": num_or_none(m.get("views", a.get("views"))),
                "likes": num_or_none(m.get("likes", a.get("likes"))),
                "comments": num_or_none(m.get("replies", a.get("replies"))),
                "linkClicks": None,        # 系統未逐則記錄連結點擊
                "registrations": None,     # 系統未逐則記錄註冊
                "note": note,
                "_src": "thread_activities",
            })
    return out


def from_posts(rows, name_to_code):
    """發文追蹤 → 貼文。"""
    out = []
    for p in rows:
        date = (p.get("date") or "")[:10]
        if not date:
            continue
        persona_name = p.get("personaName") or None
        code = resolve_code(persona_name, name_to_code)
        url = p.get("postUrl") or None
        note = p.get("topic") or p.get("articleTitle") or None
        # impressions 優先 views，再 reach
        imp = p.get("views")
        if imp in (None, "", 0):
            imp = p.get("reach")
        utm = (p.get("utmContent") or "").strip() or parse_utm_content(url)
        out.append({
            "date": date,
            "persona": code,
            "personaName": persona_name,
            "platform": norm_platform(p.get("platform")),
            "postUrl": url,
            "utmContent": utm or None,
            "impressions": num_or_none(imp),
            "likes": num_or_none(p.get("likes")),
            "comments": num_or_none(p.get("comments")),
            "linkClicks": None,
            "registrations": None,
            "note": note,
            "_src": "posts",
        })
    return out


def from_channel_posts(rows, name_to_code):
    """匿名社群發文(seeding) + 臉書社團/粉專(fb) → 貼文。指標社群端不逐則記錄，僅帶 utmContent 供 GA4 join。"""
    out = []
    for p in rows:
        date = (p.get("date") or "")[:10]
        if not date:
            continue
        channel = p.get("channel") or "seeding"
        persona_name = p.get("roleName") or None
        code = (p.get("role") or "").strip() or resolve_code(persona_name, name_to_code)
        platform = "fb" if channel == "fb" else norm_platform(p.get("platform"))
        utm = (p.get("utmContent") or "").strip() or parse_utm_content(p.get("url"))
        out.append({
            "date": date,
            "persona": code or None,
            "personaName": persona_name,
            "platform": platform,
            "postUrl": p.get("url") or p.get("shortLink") or None,
            "utmContent": utm or None,
            "impressions": None,
            "likes": None,
            "comments": None,
            "linkClicks": None,
            "registrations": None,
            "note": p.get("title") or p.get("note") or None,
            "_src": "channel_posts",
        })
    return out


def dedupe(posts):
    """以 (postUrl, platform) 去重；thread_activities 較完整優先保留。"""
    seen, out = {}, []
    for p in posts:
        key = (p.get("postUrl"), p.get("platform"))
        if p.get("postUrl") and key in seen:
            continue
        if p.get("postUrl"):
            seen[key] = True
        out.append(p)
    return out


def within_window(posts, days):
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    return [p for p in posts if p["date"] >= cutoff]


# ═══════════════════════════════════════════════════════════════
# daily 彙總（沒資料的指標 → null，不補 0）
# ═══════════════════════════════════════════════════════════════

def build_daily(posts):
    by_date = {}
    for p in posts:
        d = by_date.setdefault(p["date"], {"imp": [], "clk": [], "reg": []})
        if p["impressions"] is not None:
            d["imp"].append(p["impressions"])
        if p["linkClicks"] is not None:
            d["clk"].append(p["linkClicks"])
        if p["registrations"] is not None:
            d["reg"].append(p["registrations"])
    daily = []
    for date in sorted(by_date.keys(), reverse=True):
        d = by_date[date]
        daily.append({
            "date": date,
            "totalImpressions": sum(d["imp"]) if d["imp"] else None,
            "totalLinkClicks": sum(d["clk"]) if d["clk"] else None,
            "totalRegistrations": sum(d["reg"]) if d["reg"] else None,
        })
    return daily


# ═══════════════════════════════════════════════════════════════
# personas 輸出（主檔 + 由實際貼文推導平台）
# ═══════════════════════════════════════════════════════════════

def build_personas(master, posts):
    platforms_by_code = {}
    for p in posts:
        if p["persona"] and p["platform"]:
            platforms_by_code.setdefault(p["persona"], set()).add(p["platform"])
    out = []
    for r in master:
        code = (r.get("code") or "").strip() or None
        plats = sorted(platforms_by_code.get(code, []))
        out.append({
            "code": code,
            "name": (r.get("name") or "").strip() or None,
            "agent": (r.get("agent") or "").strip() or None,
            "platforms": plats,
        })
    return out


# ═══════════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════════

def main():
    print("🔗 抓取資料源 …")
    thread_acts = fetch_json(f"{SYS_API}/thread_activities")
    posts_raw = fetch_json(f"{SYS_API}/posts")
    try:
        channel_posts = fetch_json(f"{SYS_API}/channel_posts")
        if not isinstance(channel_posts, list):
            channel_posts = []
    except Exception:
        channel_posts = []
    master = fetch_json(f"{UTM_API}/personas")
    if not isinstance(master, list):
        master = master.get("personas") or master.get("results") or master.get("data") or []
    print(f"   thread_activities={len(thread_acts)}  posts={len(posts_raw)}  channel_posts={len(channel_posts)}  personas={len(master)}")

    name_to_code, _ = build_persona_index(master)

    posts = (from_thread_activities(thread_acts, name_to_code)
             + from_posts(posts_raw, name_to_code)
             + from_channel_posts(channel_posts, name_to_code))
    posts = dedupe(posts)
    posts = within_window(posts, DAYS_WINDOW)
    posts.sort(key=lambda x: (x["date"], x.get("postUrl") or ""), reverse=True)

    # 移除內部欄位
    for p in posts:
        p.pop("_src", None)

    feed = {
        "lastUpdated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "posts": posts,
        "daily": build_daily(posts),
        "personas": build_personas(master, posts),
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(feed, f, ensure_ascii=False, indent=2)

    # 覆蓋率回報
    total = len(posts)
    with_utm = sum(1 for p in posts if p["utmContent"])
    with_code = sum(1 for p in posts if p["persona"])
    with_imp = sum(1 for p in posts if p["impressions"] is not None)
    print(f"✅ 已寫入 {OUTPUT_FILE}")
    print(f"   posts={total}  日期區間={posts[-1]['date'] if posts else '-'} ~ {posts[0]['date'] if posts else '-'}")
    print(f"   utmContent 有值: {with_utm}/{total}（其餘 null）")
    print(f"   persona code 對上: {with_code}/{total}")
    print(f"   impressions 有值: {with_imp}/{total}")
    print(f"   linkClicks / registrations: 系統未逐則記錄 → 全 null")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"❌ 失敗: {e}", file=sys.stderr)
        sys.exit(1)
