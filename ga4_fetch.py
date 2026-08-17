#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YS89 GA4 自動數據抓取腳本
從 Google Analytics 4 拉取流量數據，生成 JSON 給 HTML 儀表板動態渲染
"""

import json
import os
import urllib.request
from datetime import datetime, timedelta
from google.oauth2 import service_account
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest, Dimension, Metric, DateRange, FilterExpression, Filter
)

# ═══════════════════════════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════════════════════════

# GA4 Property ID — ys89.fun 站群
PROPERTY_ID = "539393762"
PROPERTY_FULL = f"properties/{PROPERTY_ID}"

# picks168.com GA4 Property
PICKS168_ID = "541257936"
PICKS168_FULL = f"properties/{PICKS168_ID}"

# 四個站各有自己的 GA4 資源——LINE 圖文選單的點擊會落在該站自己的資源裡，
# 不會匯到 picks168。要看「整體加 LINE 成效」就得四個都拉，不能只拉一個。
# 2026-08-12 用服務帳號實測，四個都讀得到，主網域也都對得上：
#   541257936 picks168.com(435) / 543041773 tsaishen888.com(108)
#   543332819 dgcasnio.com(37)  / 543984577 lott168.com(19)     ※近 28 天工作階段
STATION_PROPERTIES = {
    "體育預測站": ("541257936", "picks168.com"),
    "電子站":     ("543041773", "tsaishen888.com"),
    "百家站":     ("543332819", "dgcasnio.com"),
    "彩票站":     ("543984577", "lott168.com"),
}

# Service Account JSON 路徑（GitHub Actions 會注入為環境變數）
SA_JSON_PATH = os.environ.get("GA4_SA_KEY_PATH", "./gsc-credentials.json")

# CTA 事件名稱列表（這些事件實際有觸發）
# 註：GA4 後台未把任何事件勾為「關鍵事件」→ keyEvents 一律 0（這是先前 CTA=0 的主因）。
# CTA 改用「有 CTA 事件的工作階段數(sessions)」當分子，轉換率=CTA階段/進站，必 ≤100%，
# 不用 eventCount（總點擊次數會讓單帳號轉換率破百，看起來像壞掉）。
CTA_EVENTS = [
    "platform_register_click",
    "line_click",
    "line_oa_click",
    "cta_click",
    "purchase",
]

# 水軍帳號代碼
WATER_ARMY_ACCOUNTS = {"akki", "god", "uncle", "crab", "kk"}

# ═══════════════════════════════════════════════════════════════
# 初始化 GA4 Client
# ═══════════════════════════════════════════════════════════════

def get_ga4_client():
    """認證並返回 GA4 Data API client"""
    credentials = service_account.Credentials.from_service_account_file(
        SA_JSON_PATH,
        scopes=["https://www.googleapis.com/auth/analytics.readonly"]
    )
    return BetaAnalyticsDataClient(credentials=credentials)

# ═══════════════════════════════════════════════════════════════
# 數據拉取函式
# ═══════════════════════════════════════════════════════════════

def get_date_range():
    """過去 28 天的日期範圍"""
    today = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=28)).strftime("%Y-%m-%d")
    return start, today

def get_weekly_ranges():
    """近 3 天 / 本週 7 天 / 上週 7 天 / 近 28 天 的日期範圍"""
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    return {
        "3d":    ((now - timedelta(days=2)).strftime("%Y-%m-%d"), today),
        "7d":    ((now - timedelta(days=6)).strftime("%Y-%m-%d"), today),
        "prev7d":((now - timedelta(days=13)).strftime("%Y-%m-%d"), (now - timedelta(days=7)).strftime("%Y-%m-%d")),
        "28d":   ((now - timedelta(days=27)).strftime("%Y-%m-%d"), today),
    }

def fetch_traffic_sources(client):
    """
    拉取流量來源分析
    返回: [{name, medium, sessions, cls, tag, tcls}, ...]
    """
    start_date, end_date = get_date_range()

    request = RunReportRequest(
        property=PROPERTY_FULL,
        dimensions=[
            Dimension(name="sessionSource"),
            Dimension(name="sessionMedium"),
        ],
        metrics=[
            Metric(name="sessions"),
            Metric(name="activeUsers"),
        ],
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
    )

    response = client.run_report(request)

    sources = []
    for row in response.rows:
        source = row.dimension_values[0].value
        medium = row.dimension_values[1].value
        sessions = int(row.metric_values[0].value or 0)

        if sessions == 0:
            continue

        # 分類邏輯（7 層規則）
        cls, tag, tcls = classify_traffic(source, medium)

        sources.append({
            "name": source,
            "medium": medium,
            "sessions": sessions,
            "cls": cls,
            "tag": tag,
            "tcls": tcls,
        })

    return sorted(sources, key=lambda x: x["sessions"], reverse=True)

def classify_traffic(source, medium):
    """
    水軍分類規則（7 層）
    返回: (cls, tag, tcls)
    """
    source_lower = source.lower()
    medium_lower = medium.lower() if medium else ""

    # 1. FB 廣告
    if medium_lower in ("cpc", "paid_social"):
        return "paid", "廣告", "t-paid"

    # 2. 自然搜尋
    if medium_lower == "organic":
        return "organic", "自然搜尋", "t-direct"

    # 3. 地推
    if medium_lower == "offline" or source_lower == "ditui":
        return "offline", "地推", "t-offline"

    # 4. 社群水軍
    water_army_pattern = {
        "akki", "god", "uncle", "crab", "kk", "threads", "instagram", "ig",
        "facebook", "youtube", "tiktok", "threads"
    }
    medium_water_pattern = {
        "th_post", "th_bio", "ig_post", "ig_bio", "comment", "bio",
        "social", "post", "story"
    }

    if (any(pat in source_lower for pat in water_army_pattern) or
        any(pat in medium_lower for pat in medium_water_pattern)):
        return "army", "社群水軍", "t-army"

    # 5. 直接
    if source_lower == "(direct)":
        return "direct", "直接/未知", "t-direct"

    # 6. LINE / 站內
    if "line" in source_lower or "ys89" in source_lower:
        return "line", "LINE", "t-line"

    # 7. 其他
    return "other", "其他", "t-direct"

def fetch_account_performance(client):
    """
    拉取各帳號成效（進站 vs CTA 轉換）
    """
    start_date, end_date = get_date_range()

    # 進站數據
    sessions_request = RunReportRequest(
        property=PROPERTY_FULL,
        dimensions=[Dimension(name="sessionSource")],
        metrics=[Metric(name="sessions")],
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
    )
    sessions_response = client.run_report(sessions_request)

    sessions_by_source = {}
    for row in sessions_response.rows:
        source = row.dimension_values[0].value
        sessions = int(row.metric_values[0].value or 0)
        sessions_by_source[source] = sessions

    # CTA 數據
    cta_filter = FilterExpression(
        or_group={
            "expressions": [
                FilterExpression(
                    filter=Filter(field_name="eventName", string_filter={"value": event})
                )
                for event in CTA_EVENTS
            ]
        }
    )

    cta_request = RunReportRequest(
        property=PROPERTY_FULL,
        dimensions=[Dimension(name="sessionSource")],
        metrics=[Metric(name="sessions")],
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        dimension_filter=cta_filter,
    )
    cta_response = client.run_report(cta_request)

    cta_by_source = {}
    for row in cta_response.rows:
        source = row.dimension_values[0].value
        cta = int(row.metric_values[0].value or 0)
        cta_by_source[source] = cta

    # 合併：取 sessions_by_source 中的所有來源，加上 CTA 數據
    accounts = []
    for source, sessions in sessions_by_source.items():
        cta = cta_by_source.get(source, 0)
        warn = sessions > 500 and cta == 0  # 量大但零轉換警告
        accounts.append({
            "name": source,
            "s": sessions,
            "cta": cta,
            "warn": warn,
        })

    return sorted(accounts, key=lambda x: x["s"], reverse=True)

def fetch_top_pages(client):
    """拉取熱門頁面（瀏覽次數前 7 名）"""
    start_date, end_date = get_date_range()

    request = RunReportRequest(
        property=PROPERTY_FULL,
        dimensions=[Dimension(name="pageTitle")],
        metrics=[Metric(name="screenPageViews")],
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
    )

    response = client.run_report(request)

    pages = []
    for row in response.rows:
        title = row.dimension_values[0].value
        views = int(row.metric_values[0].value or 0)
        pages.append({"t": title, "v": views})

    # 按瀏覽次數排序，取前 7 名
    pages = sorted(pages, key=lambda x: x["v"], reverse=True)[:7]
    return pages

def fetch_content_range(client, start_date, end_date):
    """依 utm_content 拆出指定區間的貼文成效"""
    cta_filter = FilterExpression(
        or_group={
            "expressions": [
                FilterExpression(
                    filter=Filter(field_name="eventName", string_filter={"value": event})
                )
                for event in CTA_EVENTS
            ]
        }
    )
    sess_req = RunReportRequest(
        property=PROPERTY_FULL,
        dimensions=[Dimension(name="sessionManualAdContent")],
        metrics=[Metric(name="sessions")],
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
    )
    sess_resp = client.run_report(sess_req)
    by_content = {}
    for row in sess_resp.rows:
        c = row.dimension_values[0].value
        s = int(row.metric_values[0].value or 0)
        if not c or c == "(not set)" or s == 0:
            continue
        by_content[c] = {"content": c, "sessions": s, "cta": 0}

    cta_req = RunReportRequest(
        property=PROPERTY_FULL,
        dimensions=[Dimension(name="sessionManualAdContent")],
        metrics=[Metric(name="sessions")],
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        dimension_filter=cta_filter,
    )
    cta_resp = client.run_report(cta_req)
    for row in cta_resp.rows:
        c = row.dimension_values[0].value
        cta = int(row.metric_values[0].value or 0)
        if c in by_content:
            by_content[c]["cta"] = cta

    return sorted(by_content.values(), key=lambda x: x["sessions"], reverse=True)

def fetch_content_performance(client):
    """依 utm_content 拆出 28 天貼文成效"""
    start_date, end_date = get_date_range()
    return fetch_content_range(client, start_date, end_date)

# ── LINE 相關流量的聚合 ────────────────────────────────────────────────
# LINE 有兩條完全不同的路徑，報表上要分開看，不能混進「社群水軍」：
#
#   ① 加好友管道  utm_medium=line_addfriend
#      IG bio / 貼文 → picks168.com/line/ 轉址頁 → LINE 加好友。
#      utm_content 是 <persona code>_<bio|post>，分得出誰帶的、放在哪。
#      注意：加好友網址本身在 line.me，GA4 追不到，所以才需要那個轉址頁。
#
#   ② 圖文選單    utm_medium=line_menu
#      已經是好友的人在 LINE 裡點選單。utm_content 是 <line_站別>_<選單代碼>。
#
# 兩者的人完全不同層：①是還沒加好友的陌生流量，②是已經加了的既有好友。
# 混在一起算會讓數字好看但失真。
def load_persona_codes():
    """收集所有「是我們自己帳號」的 code。兩邊都要拿，因為兩邊都不完整。

    實測 2026-08-12：
      UTM 產生器 50 支，但少了 pdl / yezi / nightcat 這些 seeding 帳號
      系統三個 key 聯集 40 支，但少了 shizu / crab / qiuqiusaizhan
    兩邊都還在帶流量。只取一邊的話，少掉的那幾支會被當成外部來源丟掉，
    帳號成效表上就整支消失（不是變成 0，是根本不出現，最難察覺）。

    pages.dev 擋非瀏覽器 UA（回 error 1010），所以要帶瀏覽器 UA。
    回傳 {code: 名稱}；先進來的名稱優先，UTM 產生器排最後所以不會蓋掉角色庫。
    """
    UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    codes = {}

    for key in ("personas", "community", "seeding_accounts"):
        try:
            req = urllib.request.Request(
                f"https://ys89-api.ysyyds0001.workers.dev/api/{key}",
                headers={"User-Agent": "ys89-army/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                rows = json.load(r)
            rows = rows if isinstance(rows, list) else (rows.get("data") or [])
            n = len(codes)
            for x in rows:
                c = (x.get("code") or "").strip()
                if c:
                    codes.setdefault(c, x.get("name") or c)
            print(f"   · {key}：+{len(codes) - n} 支")
        except Exception as e:
            print(f"   ⚠ {key} 讀取失敗：{e}")

    try:
        req = urllib.request.Request("https://ys89-utm.pages.dev/api/personas",
                                     headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.load(r)
        n = len(codes)
        for p in d.get("personas", []):
            if p.get("code"):
                codes.setdefault(p["code"], p.get("name") or p["code"])
        print(f"   · UTM 產生器：+{len(codes) - n} 支")
    except Exception as e:
        print(f"   ⚠ 讀不到 UTM 產生器（{e}）")

    print(f"   · 帳號 code 合計 {len(codes)} 支")
    return codes


def fetch_accounts_all(client, start_date, end_date, personas=None):
    """「誰帶進來的」——把每支帳號在所有站的進站數合起來。

    為什麼要合：同一支帳號會同時帶去多個站（財神在 ys89 站群有 80、在
    picks168 有 54），各資源只看得到自己那一份。分開看會低估，而且
    電子／百家／彩票三站原本完全沒拉，那些帳號帶進多少人都看不到。

    CTA 分子用「有 CTA 事件的工作階段數」而不是 eventCount——用 eventCount
    算過單帳號轉換率破百（曾出現 333%），分母是進站數，比值必須 ≤100%。
    """
    props = dict(STATION_PROPERTIES)
    props["ys89站群"] = (PROPERTY_ID, "ys89.fun 等")

    cta_filter = FilterExpression(or_group={"expressions": [
        FilterExpression(filter=Filter(field_name="eventName",
                                       string_filter={"value": e}))
        for e in CTA_EVENTS]})

    acc = {}   # source -> {sessions, users, cta, by_station:{}}
    for station, (pid, host) in props.items():
        prop = f"properties/{pid}"
        try:
            resp = client.run_report(RunReportRequest(
                property=prop,
                dimensions=[Dimension(name="sessionSource")],
                metrics=[Metric(name="sessions"), Metric(name="activeUsers")],
                date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            ))
            cta_resp = client.run_report(RunReportRequest(
                property=prop,
                dimensions=[Dimension(name="sessionSource")],
                metrics=[Metric(name="sessions")],
                date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
                dimension_filter=cta_filter,
            ))
            cta_map = {r.dimension_values[0].value: int(r.metric_values[0].value or 0)
                       for r in cta_resp.rows}
            n = 0
            for row in resp.rows:
                src = row.dimension_values[0].value
                s = int(row.metric_values[0].value or 0)
                if not src or s == 0:
                    continue
                a = acc.setdefault(src, {"source": src, "sessions": 0, "users": 0,
                                         "cta": 0, "by_station": {}})
                a["sessions"] += s
                a["users"]    += int(row.metric_values[1].value or 0)
                a["cta"]      += cta_map.get(src, 0)
                a["by_station"][station] = a["by_station"].get(station, 0) + s
                n += 1
            print(f"   · {station:<8} {host:<18} {n} 個來源")
        except Exception as e:
            print(f"   ⚠ {station}（{pid}）失敗，跳過：{e}")

    # 標出哪些是我們自己的帳號。personas 給不出來時就不標，**不要用猜的**——
    # 猜錯會讓 google/bing 這種外部來源被當成水軍帳號算進成效裡。
    codes = set(personas or [])
    for a in acc.values():
        a["is_account"] = a["source"] in codes if codes else None
        a["cta_rate"] = round(a["cta"] / a["sessions"] * 100, 1) if a["sessions"] else 0
    return sorted(acc.values(), key=lambda x: -x["sessions"])


def fetch_line_contents(client, start_date, end_date):
    """四個站的 utm_content 全部拉回來，每筆標上站別。

    一站掛掉不影響其他站——某個資源沒權限或暫時失敗時，回報後跳過，
    而不是整個 line 欄變空的（那樣看起來會像「沒人點」，是最糟的失敗方式）。

    同時拉 sessionSource / sessionMedium：加好友轉址頁（picks168.com/line/）
    在轉址前一律把 utm_medium 蓋成 line_addfriend、utm_source 蓋成 ch（帳號代碼），
    但 utm_content 如果原始連結有帶 pid（貼文編號，例如 cyq-0817-1）會保留 pid，
    不會是 <code>_bio/<code>_post 的格式。只看 content 字串結尾的舊邏輯會把這種
    「LINE 加好友但帶貼文編號」的點擊漏掉，要靠 medium 才抓得到。
    """
    rows = []
    for station, (pid, host) in STATION_PROPERTIES.items():
        try:
            resp = client.run_report(RunReportRequest(
                property=f"properties/{pid}",
                dimensions=[Dimension(name="sessionManualAdContent"),
                            Dimension(name="sessionSource"),
                            Dimension(name="sessionMedium")],
                metrics=[Metric(name="sessions"), Metric(name="activeUsers")],
                date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            ))
            n = 0
            for row in resp.rows:
                content = row.dimension_values[0].value
                source  = row.dimension_values[1].value
                medium  = row.dimension_values[2].value
                s = int(row.metric_values[0].value or 0)
                if not content or content == "(not set)" or s == 0:
                    continue
                rows.append({
                    "content":  content,
                    "source":   source,
                    "medium":   medium,
                    "sessions": s,
                    "users":    int(row.metric_values[1].value or 0),
                    "station":  station,
                    "host":     host,
                })
                n += 1
            print(f"   · {station} {host}：{n} 筆 utm_content")
        except Exception as e:
            print(f"   ⚠ {station}（{pid}）拉取失敗，跳過：{e}")
    return rows


def aggregate_line(contents):
    """把 contents 依 LINE 的兩條路徑分組。contents 已含所有 utm_content。

    加好友判斷改用 medium == line_addfriend（轉址頁強制蓋上的，可靠），
    不再只看 content 字串是不是 _bio/_post 結尾——帶 pid（貼文編號）的
    加好友連結 content 會是貼文編號本身，字串比對抓不到，之前會整筆消失。
    channel 優先用 source（轉址頁同樣把它蓋成 ch，比從 content 字串反推準）。
    """
    join, menu = [], []
    for c in contents or []:
        name   = str(c.get("content") or "")
        medium = str(c.get("medium") or "")
        source = str(c.get("source") or "")
        if medium == "line_addfriend":
            if name.endswith("_bio") or name.endswith("_post"):
                code, _, at = name.rpartition("_")
                channel = code or source or "unknown"
            else:
                channel, at = (source or "unknown"), "post"
            join.append({**c, "channel": channel, "placement": at})
        elif name.startswith("line_"):
            parts = name.split("_")
            menu.append({**c, "oa": "_".join(parts[:2]), "item": parts[-1]})
    key = lambda x: -x.get("sessions", 0)
    return {
        "加好友管道": sorted(join, key=key),
        "圖文選單": sorted(menu, key=key),
        "_說明": "加好友＝還沒加的陌生流量（經 picks168.com/line/ 轉址頁）；"
                 "圖文選單＝已經是好友的人在 LINE 內點擊。兩者不可合計。",
    }


SOCIAL_MEDIUMS = ["th_post", "th_bio", "ig_post", "ig_bio", "social", "post", "story", "comment", "bio"]

def fetch_kpis_range(client, start_date, end_date):
    """拉取指定日期範圍的 KPI，五個 GA4 資源合計（ys89 站群 + 四站）。

    2026-08-17 修掉一個從一開始就在的根本性 bug：這支只查過 PROPERTY_FULL
    （539393762，ys89 站群），從沒查過 picks168/tsaishen888/dgcasnio/lott168。
    實測 8/10-8/14：539393762 完全沒有 picks168.com、tsaishen888.com 的流量
    （0 場工作階段），但我們幾乎所有 UTM 貼文連結（th_post/ig_bio）導的都是
    這四個站，不是 ys89.fun 家族網域。結果就是「GA4 Sessions」「社群連結
    點擊」這些核心 KPI 卡片,量到的幾乎是另一批不相干的網域流量,不是我們
    真正在追蹤的社群導流──社群連結點擊那格常年個位數字，就是這樣來的。
    跟 fetch_accounts_all() 用同一套 STATION_PROPERTIES，五個資源都查、
    加總，才是「這段期間我們真正帶進站多少人」的完整數字。
    """
    props = dict(STATION_PROPERTIES)
    props["ys89站群"] = (PROPERTY_ID, "ys89.fun 等")

    cta_filter = FilterExpression(or_group={"expressions": [
        FilterExpression(filter=Filter(field_name="eventName", string_filter={"value": e}))
        for e in CTA_EVENTS]})
    social_filter = FilterExpression(or_group={"expressions": [
        FilterExpression(filter=Filter(field_name="sessionMedium", string_filter={"value": m}))
        for m in SOCIAL_MEDIUMS]})

    active_users = sessions = event_count = engaged_sessions = cta = social_clicks = 0
    for station, (pid, host) in props.items():
        prop = f"properties/{pid}"
        try:
            resp = client.run_report(RunReportRequest(
                property=prop,
                metrics=[Metric(name="activeUsers"), Metric(name="sessions"),
                         Metric(name="eventCount"), Metric(name="engagedSessions")],
                date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            ))
            if resp.rows:
                row = resp.rows[0]
                active_users     += int(row.metric_values[0].value or 0)
                sessions         += int(row.metric_values[1].value or 0)
                event_count      += int(row.metric_values[2].value or 0)
                engaged_sessions += int(row.metric_values[3].value or 0)

            cta_resp = client.run_report(RunReportRequest(
                property=prop, metrics=[Metric(name="sessions")],
                date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
                dimension_filter=cta_filter))
            if cta_resp.rows:
                cta += int(cta_resp.rows[0].metric_values[0].value or 0)

            social_resp = client.run_report(RunReportRequest(
                property=prop, metrics=[Metric(name="sessions")],
                date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
                dimension_filter=social_filter))
            if social_resp.rows:
                social_clicks += int(social_resp.rows[0].metric_values[0].value or 0)
        except Exception as e:
            print(f"   ⚠ KPI {station}（{pid}）失敗，跳過：{e}")

    conversion_rate = (cta / sessions * 100) if sessions > 0 else 0

    return {
        "activeUsers": active_users,
        "sessions": sessions,
        "eventCount": event_count,
        "engagedSessions": engaged_sessions,
        "socialClicks": social_clicks,
        "cta": cta,
        "conversionRate": round(conversion_rate, 2),
    }

def fetch_kpis(client):
    """拉取 KPI（28 天）"""
    start_date, end_date = get_date_range()
    return fetch_kpis_range(client, start_date, end_date)

def fetch_accounts_range(client, start_date, end_date):
    """拉取指定日期範圍的帳號成效 Top 5"""
    sess_req = RunReportRequest(
        property=PROPERTY_FULL,
        dimensions=[Dimension(name="sessionSource")],
        metrics=[Metric(name="sessions")],
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
    )
    sess_resp = client.run_report(sess_req)
    sessions_by_source = {}
    for row in sess_resp.rows:
        source = row.dimension_values[0].value
        sessions = int(row.metric_values[0].value or 0)
        sessions_by_source[source] = sessions

    cta_filter = FilterExpression(
        or_group={
            "expressions": [
                FilterExpression(
                    filter=Filter(field_name="eventName", string_filter={"value": event})
                )
                for event in CTA_EVENTS
            ]
        }
    )
    cta_req = RunReportRequest(
        property=PROPERTY_FULL,
        dimensions=[Dimension(name="sessionSource")],
        metrics=[Metric(name="sessions")],
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        dimension_filter=cta_filter,
    )
    cta_resp = client.run_report(cta_req)
    cta_by_source = {}
    for row in cta_resp.rows:
        source = row.dimension_values[0].value
        cta_by_source[source] = int(row.metric_values[0].value or 0)

    accounts = []
    for source, s in sessions_by_source.items():
        cta = cta_by_source.get(source, 0)
        accounts.append({"name": source, "s": s, "cta": cta})

    return sorted(accounts, key=lambda x: x["s"], reverse=True)[:5]

# ═══════════════════════════════════════════════════════════════
# picks168.com 數據拉取
# ═══════════════════════════════════════════════════════════════

def fetch_picks168_kpis(client, start_date, end_date):
    """picks168.com 基礎 KPI（users / sessions / events）"""
    try:
        req = RunReportRequest(
            property=PICKS168_FULL,
            metrics=[
                Metric(name="activeUsers"),
                Metric(name="sessions"),
                Metric(name="eventCount"),
            ],
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        )
        resp = client.run_report(req)
        row = resp.rows[0]
        return {
            "users":    int(row.metric_values[0].value or 0),
            "sessions": int(row.metric_values[1].value or 0),
            "events":   int(row.metric_values[2].value or 0),
        }
    except Exception as e:
        print(f"   ⚠ picks168 KPI 失敗：{e}")
        return {"users": 0, "sessions": 0, "events": 0}

def fetch_picks168_by_source(client, start_date, end_date):
    """picks168.com 按 UTM source + medium 分析流量"""
    try:
        req = RunReportRequest(
            property=PICKS168_FULL,
            dimensions=[
                Dimension(name="sessionSource"),
                Dimension(name="sessionMedium"),
            ],
            metrics=[
                Metric(name="sessions"),
                Metric(name="activeUsers"),
            ],
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        )
        resp = client.run_report(req)
        rows = []
        for row in resp.rows:
            s = int(row.metric_values[0].value or 0)
            if s == 0:
                continue
            rows.append({
                "source":  row.dimension_values[0].value,
                "medium":  row.dimension_values[1].value,
                "sessions": s,
                "users":   int(row.metric_values[1].value or 0),
            })
        return sorted(rows, key=lambda x: x["sessions"], reverse=True)
    except Exception as e:
        print(f"   ⚠ picks168 by-source 失敗：{e}")
        return []

def fetch_picks168_events(client, start_date, end_date):
    """picks168.com 全部事件清單（含次數），用來確認哪些轉化事件有被追蹤"""
    try:
        req = RunReportRequest(
            property=PICKS168_FULL,
            dimensions=[Dimension(name="eventName")],
            metrics=[Metric(name="eventCount")],
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        )
        resp = client.run_report(req)
        events = []
        for row in resp.rows:
            count = int(row.metric_values[0].value or 0)
            if count == 0:
                continue
            events.append({
                "name":  row.dimension_values[0].value,
                "count": count,
            })
        return sorted(events, key=lambda x: x["count"], reverse=True)
    except Exception as e:
        print(f"   ⚠ picks168 events 失敗：{e}")
        return []

def fetch_picks168_conversions_by_source(client, start_date, end_date):
    """picks168 轉化事件（cta_click / subscribe_click）按 UTM source 拆分"""
    CONV_EVENTS = ["cta_click", "subscribe_click"]
    result = {}
    for event in CONV_EVENTS:
        try:
            req = RunReportRequest(
                property=PICKS168_FULL,
                dimensions=[
                    Dimension(name="sessionSource"),
                    Dimension(name="sessionMedium"),
                ],
                metrics=[Metric(name="eventCount")],
                date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
                dimension_filter=FilterExpression(
                    filter=Filter(field_name="eventName", string_filter={"value": event})
                ),
            )
            resp = client.run_report(req)
            rows = []
            for row in resp.rows:
                count = int(row.metric_values[0].value or 0)
                if count == 0:
                    continue
                rows.append({
                    "source": row.dimension_values[0].value,
                    "medium": row.dimension_values[1].value,
                    "count":  count,
                })
            result[event] = sorted(rows, key=lambda x: x["count"], reverse=True)
        except Exception as e:
            print(f"   ⚠ picks168 {event} by-source 失敗：{e}")
            result[event] = []
    return result

def fetch_picks168_by_content(client, start_date, end_date):
    """picks168.com 按 utm_content 分析（追蹤哪篇貼文帶來的流量）"""
    try:
        req = RunReportRequest(
            property=PICKS168_FULL,
            dimensions=[Dimension(name="sessionManualAdContent")],
            metrics=[Metric(name="sessions"), Metric(name="activeUsers")],
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        )
        resp = client.run_report(req)
        rows = []
        for row in resp.rows:
            content = row.dimension_values[0].value
            s = int(row.metric_values[0].value or 0)
            if not content or content == "(not set)" or s == 0:
                continue
            rows.append({
                "content":  content,
                "sessions": s,
                "users":    int(row.metric_values[1].value or 0),
            })
        return sorted(rows, key=lambda x: x["sessions"], reverse=True)
    except Exception as e:
        print(f"   ⚠ picks168 by-content 失敗：{e}")
        return []

# ═══════════════════════════════════════════════════════════════
# 自訂日期查詢（給 dashboard_server.py 調用）
# ═══════════════════════════════════════════════════════════════

def fetch_accounts_range_full(client, start_date, end_date):
    """拉取指定日期範圍的所有帳號成效（不限前 5）"""
    sess_req = RunReportRequest(
        property=PROPERTY_FULL,
        dimensions=[Dimension(name="sessionSource")],
        metrics=[Metric(name="sessions")],
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
    )
    sess_resp = client.run_report(sess_req)
    sessions_by_source = {}
    for row in sess_resp.rows:
        source = row.dimension_values[0].value
        sessions = int(row.metric_values[0].value or 0)
        sessions_by_source[source] = sessions

    cta_filter = FilterExpression(
        or_group={
            "expressions": [
                FilterExpression(
                    filter=Filter(field_name="eventName", string_filter={"value": event})
                )
                for event in CTA_EVENTS
            ]
        }
    )
    cta_req = RunReportRequest(
        property=PROPERTY_FULL,
        dimensions=[Dimension(name="sessionSource")],
        metrics=[Metric(name="sessions")],
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        dimension_filter=cta_filter,
    )
    cta_resp = client.run_report(cta_req)
    cta_by_source = {}
    for row in cta_resp.rows:
        source = row.dimension_values[0].value
        cta_by_source[source] = int(row.metric_values[0].value or 0)

    accounts = []
    for source, s in sessions_by_source.items():
        cta = cta_by_source.get(source, 0)
        accounts.append({"name": source, "s": s, "cta": cta})

    return sorted(accounts, key=lambda x: x["s"], reverse=True)


def fetch_custom_range_data(client, start_date, end_date):
    """自訂日期區間的完整 GA4 數據（ys89.fun + picks168）"""
    print(f"  → ys89 KPI...")
    kpis = fetch_kpis_range(client, start_date, end_date)

    print(f"  → ys89 帳號...")
    accounts = fetch_accounts_range_full(client, start_date, end_date)

    print(f"  → ys89 貼文成效...")
    try:
        contents = fetch_content_range(client, start_date, end_date)
    except Exception as e:
        print(f"    ⚠ contents 失敗：{e}")
        contents = []

    print(f"  → picks168...")
    p168 = {
        "kpis":     fetch_picks168_kpis(client, start_date, end_date),
        "sources":  fetch_picks168_by_source(client, start_date, end_date),
        "events":   fetch_picks168_events(client, start_date, end_date),
        "conversions_by_source": fetch_picks168_conversions_by_source(client, start_date, end_date),
        "contents": fetch_picks168_by_content(client, start_date, end_date),
    }

    return {
        "custom":   True,
        "range":    f"{start_date}~{end_date}",
        "kpis":     kpis,
        "accounts": accounts,
        "contents": contents,
        "picks168": p168,
    }


# ═══════════════════════════════════════════════════════════════
# 主程式
# ═══════════════════════════════════════════════════════════════

def main():
    """主程式：拉取所有數據並生成 JSON"""
    print("🔌 初始化 GA4 連接...")
    client = get_ga4_client()

    print("📊 拉取流量來源...")
    sources = fetch_traffic_sources(client)

    print("👥 拉取各帳號成效...")
    accounts = fetch_account_performance(client)

    print("📄 拉取熱門頁面...")
    pages = fetch_top_pages(client)

    print("📝 拉取單篇貼文成效（utm_content）...")
    try:
        contents = fetch_content_performance(client)
    except Exception as e:
        print(f"   ⚠ utm_content 維度拉取失敗（先給空）：{e}")
        contents = []

    print("📈 拉取 KPI...")
    kpis = fetch_kpis(client)

    print("📅 拉取多區間 KPI（3天/7天/上週/28天）...")
    ranges = get_weekly_ranges()
    period_kpis    = {}
    period_accts   = {}
    period_contents = {}
    for key, (s, e) in ranges.items():
        period_kpis[key]    = fetch_kpis_range(client, s, e)
        period_accts[key]   = fetch_accounts_range(client, s, e)
        if key in ("3d", "7d"):
            print(f"   📝 拉取 {key} 貼文成效...")
            try:
                period_contents[key] = fetch_content_range(client, s, e)
            except Exception as ex:
                print(f"   ⚠ {key} 貼文成效失敗：{ex}")
                period_contents[key] = []

    print("🏪 拉取 picks168.com 數據...")
    p_start, p_end = get_date_range()
    picks168_data = {
        "kpis_28d":    fetch_picks168_kpis(client, p_start, p_end),
        "kpis_7d":     fetch_picks168_kpis(client, *ranges["7d"]),
        "kpis_prev7d": fetch_picks168_kpis(client, *ranges["prev7d"]),
        "sources_28d": fetch_picks168_by_source(client, p_start, p_end),
        "sources_7d":  fetch_picks168_by_source(client, *ranges["7d"]),
        "events_28d":   fetch_picks168_events(client, p_start, p_end),
        "events_7d":    fetch_picks168_events(client, *ranges["7d"]),
        "conversions_by_source_28d": fetch_picks168_conversions_by_source(client, p_start, p_end),
        "conversions_by_source_7d":  fetch_picks168_conversions_by_source(client, *ranges["7d"]),
        "contents_28d": fetch_picks168_by_content(client, p_start, p_end),
        "contents_7d":  fetch_picks168_by_content(client, *ranges["7d"]),
    }

    print("💬 拉取四站的 LINE 數據（加好友管道 / 圖文選單）...")
    line_data = aggregate_line(fetch_line_contents(client, p_start, p_end))
    line_data["_期間"] = f"{p_start}~{p_end}"

    print("👤 拉取「誰帶進來的」（五個資源合計）...")
    persona_names = load_persona_codes()
    accounts_all = fetch_accounts_all(client, p_start, p_end, list(persona_names))
    for a in accounts_all:
        a["name"] = persona_names.get(a["source"], a["source"])
    accounts_all_data = {
        "_期間": f"{p_start}~{p_end}",
        "_說明": "每支帳號在所有站的進站合計。同一支會同時帶去多個站，"
                 "各資源分開看會低估。CTA 用『有 CTA 事件的工作階段數』，"
                 "轉換率＝CTA階段/進站，必 ≤100%。",
        "帳號":     [a for a in accounts_all if a.get("is_account")],
        "其他來源": [a for a in accounts_all if not a.get("is_account")][:20],
    }

    # 組合數據
    ga4_data = {
        "sources": sources,
        "accounts": accounts,
        "pages": pages,
        "contents":     contents,
        "contents_3d":  period_contents.get("3d", []),
        "contents_7d":  period_contents.get("7d", []),
        "kpis": kpis,
        "kpis_3d":      period_kpis["3d"],
        "kpis_7d":      period_kpis["7d"],
        "kpis_prev7d":  period_kpis["prev7d"],
        "kpis_28d":     period_kpis["28d"],
        "accounts_3d":  period_accts["3d"],
        "accounts_7d":  period_accts["7d"],
        "accounts_prev7d": period_accts["prev7d"],
        "accounts_28d": period_accts["28d"],
        "ranges": {k: f"{v[0]}~{v[1]}" for k, v in ranges.items()},
        "line": line_data,
        "accounts_all": accounts_all_data,
        "picks168": picks168_data,
        "lastUpdated": datetime.now().isoformat(),
    }

    # 寫入 JSON
    output_file = "./ga4-data.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(ga4_data, f, ensure_ascii=False, indent=2)

    print(f"✅ 數據已存儲：{output_file}")
    print(f"   - 流量來源：{len(sources)} 條")
    print(f"   - 帳號成效：{len(accounts)} 條")
    print(f"   - 熱門頁面：{len(pages)} 條")
    print(f"   - 總活躍使用者：{kpis['activeUsers']}")
    print(f"   - 總工作階段：{kpis['sessions']}")
    print(f"   - CTA 轉換：{kpis['cta']} / {kpis['conversionRate']}%")
    p = picks168_data["kpis_28d"]
    print(f"   - picks168 28d sessions：{p['sessions']}，events：{p['events']}")
    print(f"   - picks168 事件類型：{[e['name'] for e in picks168_data['events_28d'][:5]]}")

if __name__ == "__main__":
    main()
