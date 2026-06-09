#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
熱話題追蹤計數系統
自動計算每日帖子數量、互動量、趨勢
"""

import csv
import json
from datetime import datetime, timedelta
from collections import defaultdict

def load_tracker_data(filepath='hot-topics-tracker.csv'):
    """載入熱話題追蹤數據"""
    data = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            data = list(reader)
    except FileNotFoundError:
        print(f"❌ 找不到 {filepath}")
    return data

def count_posts_by_date(data):
    """按日期計算帖子數量"""
    counts = defaultdict(int)
    for row in data:
        date = row.get('日期', '')
        posts = int(row.get('帖子數', 0))
        counts[date] += posts
    return dict(sorted(counts.items(), reverse=True))

def count_posts_by_account(data):
    """按帳號計算帖子數量"""
    counts = defaultdict(int)
    for row in data:
        account = row.get('帳號', '')
        posts = int(row.get('帖子數', 0))
        counts[account] += posts
    return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))

def count_posts_by_platform(data):
    """按平台計算帖子數量"""
    counts = defaultdict(int)
    for row in data:
        platform = row.get('平台', '')
        posts = int(row.get('帖子數', 0))
        counts[platform] += posts
    return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))

def get_top_topics(data, limit=10):
    """獲取熱門話題"""
    topics = []
    for row in data:
        topics.append({
            'topic': row.get('話題', ''),
            'account': row.get('帳號', ''),
            'posts': int(row.get('帖子數', 0)),
            'engagement': int(row.get('互動量', 0)),
            'date': row.get('日期', '')
        })
    return sorted(topics, key=lambda x: x['engagement'], reverse=True)[:limit]

def generate_report(data):
    """生成每日報告"""
    report = {
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'total_posts': sum(int(row.get('帖子數', 0)) for row in data),
            'total_engagement': sum(int(row.get('互動量', 0)) for row in data),
            'unique_accounts': len(set(row.get('帳號', '') for row in data)),
            'unique_platforms': len(set(row.get('平台', '') for row in data))
        },
        'by_date': count_posts_by_date(data),
        'by_account': count_posts_by_account(data),
        'by_platform': count_posts_by_platform(data),
        'top_topics': get_top_topics(data)
    }
    return report

if __name__ == '__main__':
    # 載入數據
    data = load_tracker_data()
    
    if data:
        # 生成報告
        report = generate_report(data)
        
        # 輸出 JSON
        with open('topic-report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # 打印摘要
        print("✅ 熱話題追蹤報告已生成")
        print("")
        print(f"📊 摘要統計：")
        print(f"  總帖子數：{report['summary']['total_posts']}")
        print(f"  總互動量：{report['summary']['total_engagement']}")
        print(f"  活躍帳號：{report['summary']['unique_accounts']}")
        print(f"  覆蓋平台：{report['summary']['unique_platforms']}")
        print("")
        print(f"🏆 帖子數排名（按帳號）：")
        for account, count in list(report['by_account'].items())[:5]:
            print(f"   {account}: {count} 篇")
    else:
        print("❌ 沒有數據可處理")
