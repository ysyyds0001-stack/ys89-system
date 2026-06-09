#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import json

# 读取原始HTML
with open("index_original.html", "r", encoding="utf-8") as f:
    html = f.read()

# 读取GA4数据
with open("ga4-data.json", "r", encoding="utf-8") as f:
    ga4_data = json.load(f)

print(f"Original size: {len(html)} bytes")
print(f"GA4 sources: {len(ga4_data['sources'])}")

# 在导航栏中插入GA4标签
# 原始: <div class="nav-tab active" onclick="nav(this,'personas')">發文角色</div>
# 替换为:
# <div class="nav-tab active" onclick="nav(this,'ga4')">📊 GA4成效</div>
# <div class="nav-tab" onclick="nav(this,'personas')">發文角色</div>

nav_old = '   <div class="nav-tab active" onclick="nav(this,\'personas\')">發文角色</div>'
nav_new = '''   <div class="nav-tab active" onclick="nav(this,'ga4')">📊 GA4成效</div>
   <div class="nav-tab" onclick="nav(this,'personas')">發文角色</div>'''

html = html.replace(nav_old, nav_new)
print("✓ Navigation updated")

# 在第一个page之前添加GA4页面
ga4_page = '''  <!-- ===== PAGE: GA4成效 ===== -->
  <div id="pg-ga4" class="page active">
    <div style="margin-bottom:18px">
      <h2 style="font-size:1.2rem;font-weight:700">📊 GA4 成效分析</h2>
      <p class="tm" style="margin-top:3px">實時流量數據、帳號成效、熱門頁面分析</p>
    </div>

    <!-- KPI統計 -->
    <div class="g4" style="margin-bottom:18px" id="ga4-kpis"></div>

    <!-- 流量來源 -->
    <div class="card" style="margin-bottom:18px">
      <div class="card-title">流量來源排行</div>
      <div id="ga4-sources" style="font-size:.85rem;max-height:400px;overflow-y:auto"></div>
    </div>

    <!-- 帳號成效 -->
    <div class="card" style="margin-bottom:18px">
      <div class="card-title">帳號成效（按進站數排序）</div>
      <div id="ga4-accounts" style="font-size:.85rem;max-height:400px;overflow-y:auto"></div>
    </div>

    <!-- 熱門頁面 -->
    <div class="card">
      <div class="card-title">熱門頁面（前7）</div>
      <div id="ga4-pages"></div>
    </div>
  </div>

'''

page_marker = '  <!-- ===== PAGE: 發文角色 ===== -->'
html = html.replace(page_marker, ga4_page + page_marker)
print("✓ GA4 page added")

# 修改renders对象，添加ga4渲染函数
ga4_data_json = json.dumps(ga4_data, ensure_ascii=False)
renders_old = "const renders={personas:renderPersonas,tracker:renderTracker,articles:renderArticles,community:renderCommunity}"
renders_new = f"const ga4Data = {ga4_data_json}; const renders={{ga4:renderGA4,personas:renderPersonas,tracker:renderTracker,articles:renderArticles,community:renderCommunity}}"
html = html.replace(renders_old, renders_new)
print("✓ GA4 render function registered")

# 添加renderGA4函数
ga4_func = '''
  // ===== GA4 RENDERING =====
  function renderGA4(){
    const data = ga4Data;

    // 渲染KPI
    const kpis = data.kpis
    document.getElementById('ga4-kpis').innerHTML = [
      ['活躍用戶', kpis.activeUsers, ''],
      ['工作階段', kpis.sessions, ''],
      ['事件數', kpis.eventCount, ''],
      ['轉換率', (kpis.conversionRate||0).toFixed(2) + '%', '']
    ].map(([l,v]) => `<div class="stat"><div class="stat-num">${v}</div><div class="stat-label">${l}</div></div>`).join('')

    // 渲染流量來源（前15）
    const sourcesHtml = data.sources.slice(0,15).map((s,i) => `
      <div class="fb" style="padding:8px 0;border-bottom:1px solid var(--border)">
        <div>
          <div style="font-weight:600;font-size:.9rem">${i+1}. ${s.name}</div>
          <div class="flex" style="gap:6px;margin-top:3px">
            <span class="badge b-blue" style="font-size:.65rem">${s.medium}</span>
            <span class="badge b-green" style="font-size:.65rem">${s.tag}</span>
          </div>
        </div>
        <div style="text-align:right">
          <div style="font-weight:700;color:var(--accent);font-size:.95rem">${s.sessions.toLocaleString()}</div>
          <div class="tm" style="font-size:.7rem">次</div>
        </div>
      </div>
    `).join('')
    document.getElementById('ga4-sources').innerHTML = sourcesHtml || '<div class="tm">無數據</div>'

    // 渲染帳號成效（前12）
    const accountsHtml = data.accounts.slice(0,12).map((a,i) => {
      const badge = a.warn ? '<span class="badge b-red" style="font-size:.65rem">⚠️ 待轉換</span>' : '<span class="badge b-green" style="font-size:.65rem">✓ 正常</span>'
      return `
      <div class="fb" style="padding:8px 0;border-bottom:1px solid var(--border)">
        <div>
          <div style="font-weight:600;font-size:.9rem">${i+1}. ${a.name}</div>
          <div style="font-size:.75rem;color:var(--text3);margin-top:2px">${badge}</div>
        </div>
        <div style="text-align:right">
          <div style="font-weight:700;color:var(--accent);font-size:.95rem">${a.s.toLocaleString()}</div>
          <div class="tm" style="font-size:.7rem">進站</div>
        </div>
      </div>
      `
    }).join('')
    document.getElementById('ga4-accounts').innerHTML = accountsHtml || '<div class="tm">無數據</div>'

    // 渲染熱門頁面
    const pagesHtml = '<div style="overflow-x:auto"><table style="width:100%;font-size:.85rem"><thead><tr style="border-bottom:2px solid var(--border)"><th style="width:50px;padding:8px">排名</th><th style="padding:8px">頁面標題</th><th style="width:120px;text-align:right;padding:8px">瀏覽</th></tr></thead><tbody>' +
      data.pages.map((p,i) => `
      <tr style="border-bottom:1px solid var(--border)">
        <td style="font-weight:700;color:var(--accent);text-align:center;padding:8px">${i+1}</td>
        <td style="padding:8px">${p.t}</td>
        <td style="text-align:right;font-weight:700;color:var(--accent);padding:8px">${p.v.toLocaleString()}</td>
      </tr>
      `).join('') +
      '</tbody></table></div>'
    document.getElementById('ga4-pages').innerHTML = pagesHtml
  }
'''

# 在initData前添加renderGA4函数
init_marker = "  // ===== INIT ====="
html = html.replace(init_marker, ga4_func + "\n" + init_marker)
print("✓ GA4 rendering function added")

# 保存修改后的文件
with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

print(f"\nModified size: {len(html)} bytes")
print(f"✅ Saved to index.html")
