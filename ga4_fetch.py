#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YS89 GA4 自動數據抓取腳本
從 Google Analytics 4 拉取流量數據，生成 JSON 給 HTML 儀表板動態渲染
"""

import json
import os
from datetime import datetime, timedelta
from google.oauth2 import service_account
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest, Dimension, Metric, DateRange, FilterExpression, Filter
)

# ═══════════════════════════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════════════════════════

# GA4 Property ID
PROPERTY_ID = "539393762"
PROPERTY_FULL = f"properties/{PROPERTY_ID}"

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

def fetch_content_performance(client):
    """
    依 utm_content（貼文 ID）拆出單篇貼文成效
    返回: [{content, sessions, cta}, ...]  ← 給「成效報表」對到每一則貼文
    """
    start_date, end_date = get_date_range()

    # 各 utm_content 的工作階段
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

    # 各 utm_content 的 CTA（關鍵事件）
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

def fetch_kpis_range(client, start_date, end_date):
    """拉取指定日期範圍的 KPI"""

    request = RunReportRequest(
        property=PROPERTY_FULL,
        metrics=[
            Metric(name="activeUsers"),
            Metric(name="sessions"),
            Metric(name="eventCount"),
        ],
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
    )

    response = client.run_report(request)
    row = response.rows[0]

    active_users = int(row.metric_values[0].value or 0)
    sessions = int(row.metric_values[1].value or 0)
    event_count = int(row.metric_values[2].value or 0)

    # CTA 數（用上面的邏輯）
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
        metrics=[Metric(name="sessions")],
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        dimension_filter=cta_filter,
    )
    cta_response = client.run_report(cta_request)
    cta = int(cta_response.rows[0].metric_values[0].value or 0) if cta_response.rows else 0

    conversion_rate = (cta / sessions * 100) if sessions > 0 else 0

    return {
        "activeUsers": active_users,
        "sessions": sessions,
        "eventCount": event_count,
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
    period_kpis   = {}
    period_accts  = {}
    for key, (s, e) in ranges.items():
        period_kpis[key]  = fetch_kpis_range(client, s, e)
        period_accts[key] = fetch_accounts_range(client, s, e)

    # 組合數據
    ga4_data = {
        "sources": sources,
        "accounts": accounts,
        "pages": pages,
        "contents": contents,
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

if __name__ == "__main__":
    main()
