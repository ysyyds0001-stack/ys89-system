/* ============================================================
   YS89 儀表板 v1 — dashboard.js
   依賴：DashboardAdapter (dashboard-adapter.js)
   ============================================================ */

;(function () {
  'use strict'

  /* ---- 篩選器狀態 ---- */
  var _f = { range: '7d', customStart: '', customEnd: '', platform: 'all', persona: 'all' }

  /* ---- 公開 API ---- */
  window.renderDashboard = render
  window.dbSetRange    = function (r) { _f.range    = r;  render() }
  window.dbSetPlatform = function (p) { _f.platform = p;  render() }
  window.dbSetPersona  = function (p) { _f.persona  = p;  render() }

  /* ---- 格式化工具 ---- */
  function fmtNum(n) {
    if (n == null) return '—'
    n = +n
    if (n >= 10000) return (n / 10000).toFixed(1) + ' 萬'
    if (n >= 1000)  return (n / 1000).toFixed(1)  + 'k'
    return String(Math.round(n))
  }
  function fmtPct(p) { return p == null ? '—' : Math.round(p) + '%' }
  function todayStr() { return new Date().toISOString().slice(0, 10) }
  function mmdd(d) { return (!d || d.length < 10) ? (d || '') : (d.slice(5,7) + '/' + d.slice(8,10)) }
  function esc(s) {
    return (s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')
  }
  function groupBy(arr, fn) {
    var r = {}
    arr.forEach(function (x) { var k=fn(x); if(!r[k]) r[k]=[]; r[k].push(x) })
    return r
  }
  function uniq(arr) {
    var seen={}; return arr.filter(function(v){ if(seen[v]) return false; seen[v]=true; return true })
  }

  /* ---- 主渲染 ---- */
  function render() {
    var el = document.getElementById('pg-dashboard')
    if (!el) return

    var dates = DashboardAdapter.getDateRange(_f.range, _f.customStart, _f.customEnd)
    var now   = todayStr()

    var ta   = DashboardAdapter.threadActivities()
    var pos  = DashboardAdapter.posts()
    var cp   = DashboardAdapter.channelPosts()
    var conv = DashboardAdapter.convDaily()

    var taF   = DashboardAdapter.filterByDate(ta,   dates.start, dates.end)
    var posF  = DashboardAdapter.filterByDate(pos,  dates.start, dates.end)
    var cpF   = DashboardAdapter.filterByDate(cp,   dates.start, dates.end)
    var convF = DashboardAdapter.filterByDate(conv, dates.start, dates.end)

    if (_f.platform !== 'all') taF = taF.filter(function(a){ return (a.platform||'')===_f.platform })
    if (_f.persona  !== 'all') taF = taF.filter(function(a){ return (a.persona ||'')===_f.persona  })

    var personaList = uniq(ta.map(function(a){ return a.persona||'' }).filter(Boolean))

    el.innerHTML =
      buildFilterBar(dates, personaList) +
      '<div id="db-content">' +
      buildKPISection(taF, posF, cpF, convF) +
      buildTodaySection(ta, now) +
      buildTrendSection(ta, dates) +
      buildPlatformPersonaSection(taF) +
      buildTopContentSection(taF) +
      buildFunnelSection(taF, convF) +
      buildOptLogSection() +
      buildAlertsSection(ta) +
      '</div>'
  }

  /* ---- 篩選列 ---- */
  function buildFilterBar(dates, personaList) {
    var ranges = [{key:'today',lbl:'今日'},{key:'7d',lbl:'近 7 日'},{key:'30d',lbl:'近 30 日'}]
    var plats  = [{key:'all',lbl:'全部'},{key:'Threads',lbl:'Threads'},{key:'IG',lbl:'IG'},{key:'FB',lbl:'FB'}]

    var h = '<div id="db-filter-bar">'
    h += '<span class="db-filter-label">區間</span><div class="db-filter-group">'
    ranges.forEach(function(r){
      h += '<button class="db-btn-sm'+(_f.range===r.key?' db-active':'') + '" onclick="dbSetRange(\''+r.key+'\')">'+r.lbl+'</button>'
    })
    h += '</div><span class="db-filter-sep"></span>'
    h += '<span class="db-filter-label">平台</span><div class="db-filter-group">'
    plats.forEach(function(p){
      h += '<button class="db-btn-sm'+(_f.platform===p.key?' db-active':'') + '" onclick="dbSetPlatform(\''+p.key+'\')">'+p.lbl+'</button>'
    })
    h += '</div>'

    if (personaList.length) {
      h += '<span class="db-filter-sep"></span><span class="db-filter-label">角色</span><div class="db-filter-group">'
      h += '<button class="db-btn-sm'+(_f.persona==='all'?' db-active':'') + '" onclick="dbSetPersona(\'all\')">全部</button>'
      personaList.slice(0, 6).forEach(function(pn){
        h += '<button class="db-btn-sm'+(_f.persona===pn?' db-active':'') + '" onclick="dbSetPersona(\''+esc(pn)+'\')">'+esc(pn)+'</button>'
      })
      h += '</div>'
    }

    h += '<span class="db-date-range">'+dates.start+'  ⋯  '+dates.end+'</span>'
    h += '</div>'
    return h
  }

  /* ---- KPI 卡片 ---- */
  function buildKPISection(taF, posF, cpF, convF) {
    var pubTotal = taF.length + posF.length + cpF.length

    var taNoDel = taF.filter(function(a){ return (a.notes||'').indexOf('貼文已刪除')===-1 })
    var taMiss  = taNoDel.filter(function(a){ return !DashboardAdapter.hasMetrics(a) })

    var totalInter = 0, hasInterData = false
    taF.forEach(function(a){
      var m = DashboardAdapter.getMetrics(a)
      if (m.likes!=null || m.cmts!=null) {
        hasInterData = true
        totalInter += (m.likes||0) + (m.cmts||0) + (m.shares||0)
      }
    })

    var totalConv = 0, hasConvData = convF.length > 0
    convF.forEach(function(c){ totalConv += +(c.inq||0) + +(c.reg||0) + +(c.dep||0) })

    var taWithMet = taNoDel.filter(DashboardAdapter.hasMetrics).length
    var taTotal   = taNoDel.length
    var complete  = taTotal > 0 ? Math.round(taWithMet / taTotal * 100) : null

    function card(label, valStr, sub, cardCls, valCls, link) {
      return '<div class="db-kpi-card '+(cardCls||'')+'" onclick="AppShell.navPage(\''+link+'\')">'
           + '<div class="db-kpi-label">'+label+'</div>'
           + '<div class="db-kpi-val '+(valCls||'')+'">'+valStr+'</div>'
           + '<div class="db-kpi-sub">'+sub+'</div>'
           + '</div>'
    }

    return '<div class="db-sec"><div class="db-sec-title">核心指標</div><div class="db-kpi-row">'
      + card('本期發布數',
          pubTotal > 0 ? fmtNum(pubTotal) : '0',
          'Threads '+taF.length+' · 追蹤 '+posF.length+' · 匿名 '+cpF.length,
          pubTotal > 0 ? '' : 'kc-na', pubTotal > 0 ? '' : 'kv-na', 'threadtracker')
      + card('待補成效',
          fmtNum(taMiss.length),
          '待填的 Threads 貼文數',
          taMiss.length > 0 ? 'kc-warn' : 'kc-ok',
          taMiss.length > 0 ? 'kv-warn' : 'kv-ok', 'threadtracker')
      + card('總互動',
          hasInterData ? fmtNum(totalInter) : '尚未串接',
          hasInterData ? '讚＋留言＋轉發（Threads）' : '區間無 Threads 成效資料',
          hasInterData ? '' : 'kc-na', hasInterData ? '' : 'kv-na', 'threadtracker')
      + card('連結點擊',
          '尚未串接',
          '需串接 GA4 或短連結 API',
          'kc-na', 'kv-na', 'ga4')
      + card('完成轉換',
          hasConvData ? fmtNum(totalConv) : '—',
          hasConvData ? '詢問＋登記＋儲值' : '尚未串接或無資料',
          hasConvData ? '' : 'kc-na', hasConvData ? '' : 'kv-na', 'conv')
      + card('資料完整率',
          fmtPct(complete),
          taTotal > 0 ? (taWithMet+' / '+taTotal+' 則已填成效') : '無 Threads 發布記錄',
          complete==null ? 'kc-na' : complete>=80 ? 'kc-ok' : complete<50 ? 'kc-warn' : '',
          complete==null ? 'kv-na' : complete>=80 ? 'kv-ok' : complete<50 ? 'kv-warn' : '',
          'threadtracker')
      + '</div></div>'
  }

  /* ---- 今日概況 (operator only) ---- */
  function buildTodaySection(ta, now) {
    var taToday   = ta.filter(function(a){ return DashboardAdapter.dateOf(a)===now })
    var taDone    = taToday.filter(DashboardAdapter.hasMetrics)
    var taPend    = taToday.filter(function(a){ return !DashboardAdapter.hasMetrics(a) && (a.notes||'').indexOf('貼文已刪除')===-1 })
    var taAllMiss = ta.filter(function(a){ return !DashboardAdapter.hasMetrics(a) && (a.notes||'').indexOf('貼文已刪除')===-1 })

    function box(val, lbl, warn, hint) {
      var v = val==null ? '—' : String(val)
      return '<div class="db-today-stat"><div class="dt-num'+(warn?' warn':'')+'">'+v+'</div>'
           + '<div class="dt-lbl">'+lbl+(hint?'<br><span style="font-size:.6rem">'+hint+'</span>':'')+'</div></div>'
    }

    return '<div class="db-sec db-operator-only">'
      + '<div class="db-sec-title">今日概況</div>'
      + '<div class="db-quick-actions">'
      + '<button class="db-qa-btn" onclick="AppShell.navPage(\'threadtracker\')">🔥 社群炒群</button>'
      + '<button class="db-qa-btn" onclick="AppShell.navPage(\'channel\')">📝 匿名社群</button>'
      + '<button class="db-qa-btn" onclick="AppShell.navPage(\'channelfb\')">📘 Facebook 社團</button>'
      + '<button class="db-qa-btn" onclick="AppShell.navPage(\'conv\')">💰 記錄轉化</button>'
      + '<button class="db-qa-btn" onclick="AppShell.navPage(\'ga4\')">📊 成效總結</button>'
      + '</div>'
      + '<div class="db-today-row">'
      + box(taToday.length, '今日社群炒群')
      + box(taDone.length,  '今日已補成效')
      + box(taPend.length,  '今日待補成效', taPend.length > 0)
      + box(taAllMiss.length, '全部待補成效', taAllMiss.length > 3)
      + box(null, '異常連結', false, '尚未串接')
      + '</div></div>'
  }

  /* ---- 成效趨勢 ---- */
  function buildTrendSection(ta, dates) {
    var days = []
    var cur = new Date(dates.start + 'T00:00:00')
    var end = new Date(dates.end   + 'T00:00:00')
    while (cur <= end) { days.push(cur.toISOString().slice(0,10)); cur.setDate(cur.getDate()+1) }
    if (days.length > 30) days = days.slice(days.length - 30)

    var pubBy = {}, interBy = {}
    days.forEach(function(d){ pubBy[d]=0; interBy[d]=0 })
    ta.forEach(function(a){
      var d = DashboardAdapter.dateOf(a)
      if (pubBy[d]===undefined) return
      pubBy[d]++
      var m = DashboardAdapter.getMetrics(a)
      interBy[d] += (m.likes||0)+(m.cmts||0)+(m.shares||0)
    })

    var pubVals   = days.map(function(d){ return pubBy[d] })
    var interVals = days.map(function(d){ return interBy[d] })
    var hasPub   = pubVals.some(function(v){ return v>0 })
    var hasInter = interVals.some(function(v){ return v>0 })

    function bars(vals, isAlt) {
      var mx = Math.max.apply(null,vals) || 1
      return '<div class="db-bar-wrap">' + days.map(function(d,i){
        var h = Math.max(2, Math.round(vals[i]/mx*68))
        var showLbl = days.length<=14 || i%7===0 || i===days.length-1
        return '<div class="db-bar-col" title="'+d+': '+vals[i]+'">'
             + '<div class="db-bar'+(isAlt?' db-bar-alt':'')+'" style="height:'+h+'px"></div>'
             + '<span class="db-bar-lbl">'+(showLbl?mmdd(d):'')+'</span>'
             + '</div>'
      }).join('') + '</div>'
    }

    return '<div class="db-sec"><div class="db-sec-title">成效趨勢</div>'
      + '<div class="db-trend-row">'
      + '<div class="db-chart-card"><div class="db-chart-title">每日發布數（Threads）</div>'
      + (hasPub ? bars(pubVals,false) : '<div class="db-chart-na">此區間無發布資料</div>')
      + '</div>'
      + '<div class="db-chart-card"><div class="db-chart-title">每日互動數（讚＋留言＋轉發）</div>'
      + (hasInter ? bars(interVals,true) : '<div class="db-chart-na">此區間無互動資料</div>')
      + '</div>'
      + '</div></div>'
  }

  /* ---- 平台與角色表現（同一個 section，兩欄） ---- */
  function buildPlatformPersonaSection(taF) {
    return '<div class="db-sec"><div class="db-sec-title">平台與角色表現</div>'
         + '<div class="db-table-row">'
         + rankCard(taF, function(a){ return a.platform||'未知' }, '平台發布量 · 互動')
         + rankCard(taF, function(a){ return a.persona ||'未知' }, '角色排行（互動）')
         + '</div></div>'
  }

  function rankCard(taF, keyFn, title) {
    var byKey = groupBy(taF, keyFn)
    var items = Object.keys(byKey).map(function(k){
      var arr = byKey[k], inter=0, hasMet=false
      arr.forEach(function(a){
        var m = DashboardAdapter.getMetrics(a)
        if (m.likes!=null||m.cmts!=null){ hasMet=true; inter+=(m.likes||0)+(m.cmts||0)+(m.shares||0) }
      })
      return { name:k, count:arr.length, inter: hasMet?inter:null }
    })
    items.sort(function(a,b){
      return (b.inter!=null?b.inter:b.count) - (a.inter!=null?a.inter:a.count)
    })
    var maxI = items.reduce(function(m,s){ return Math.max(m, s.inter||0) },0) || 1

    var h = '<div class="db-rank-card"><div class="db-rank-title">'+title+'</div>'
    if (!items.length) {
      h += '<div class="db-rank-na">此篩選條件無資料</div>'
    } else {
      items.slice(0,5).forEach(function(s,i){
        var bw = s.inter!=null ? Math.round(s.inter/maxI*100) : 0
        h += '<div class="db-rank-item">'
           + '<span class="db-rank-num">'+(i+1)+'</span>'
           + '<span class="db-rank-name"><span class="db-rank-name-inner"><span class="db-rank-text">'+esc(s.name)+'</span>'
           + '<span class="db-rank-bar"><span class="db-rank-fill" style="width:'+bw+'%"></span></span></span></span>'
           + '<span class="db-rank-val">'+s.count+'則 · '+(s.inter!=null?fmtNum(s.inter):'—')+'</span>'
           + '</div>'
      })
    }
    return h + '</div>'
  }

  /* ---- 最佳 / 待優化內容 ---- */
  function buildTopContentSection(taF) {
    var scored = taF.map(function(a){
      var m = DashboardAdapter.getMetrics(a)
      var inter = (m.likes!=null||m.cmts!=null) ? ((m.likes||0)+(m.cmts||0)+(m.shares||0)) : -1
      return { a:a, inter:inter, m:m }
    }).filter(function(x){ return x.inter >= 0 })

    var best   = scored.slice().sort(function(a,b){ return b.inter-a.inter }).slice(0,5)
    var optim  = scored.filter(function(x){
      return x.inter === 0 || (x.m.views!=null && x.m.views<500 && x.inter<5)
    }).slice(0,5)

    function contentItem(x, i, warn) {
      var name = esc((x.a.persona||'') + (x.a.utm_content ? ' · '+x.a.utm_content : x.a.shortLink ? ' · '+x.a.shortLink : ''))
      return '<div class="db-content-item">'
           + '<span class="db-content-rank" style="'+(warn?'color:#fb923c':'')+'"> #'+(i+1)+'</span>'
           + '<div class="db-content-info"><div class="db-content-name" title="'+name+'">'+name+'</div>'
           + '<div class="db-content-meta">'+esc(x.a.date||'')+'&nbsp;·&nbsp;'+esc(x.a.platform||'')+'</div></div>'
           + '<span class="db-content-metric" style="'+(warn?'color:#fb923c':'')+'">互動&nbsp;'+fmtNum(x.inter)+'</span>'
           + '</div>'
    }

    return '<div class="db-sec"><div class="db-sec-title">最佳與待優化內容</div>'
      + '<div class="db-content-row">'
      + '<div class="db-content-card"><div class="db-content-title">⭐ 最佳內容（互動最高）</div>'
      + (best.length ? best.map(function(x,i){ return contentItem(x,i,false) }).join('')
                     : '<div class="db-content-na">此區間無成效資料</div>')
      + '</div>'
      + '<div class="db-content-card"><div class="db-content-title">⚠️ 待優化（低互動）</div>'
      + (optim.length ? optim.map(function(x,i){ return contentItem(x,i,true) }).join('')
                      : '<div class="db-content-na">'+(scored.length?'本期內容表現良好':'無成效資料')+'</div>')
      + '</div></div></div>'
  }

  /* ---- 轉換漏斗 ---- */
  function buildFunnelSection(taF, convF) {
    var published = taF.length
    var totalInter = 0
    taF.forEach(function(a){
      var m = DashboardAdapter.getMetrics(a)
      totalInter += (m.likes||0)+(m.cmts||0)+(m.shares||0)
    })
    var totalConv = 0
    convF.forEach(function(c){ totalConv += +(c.inq||0)+(c.reg||0)+(c.dep||0) })
    var hasInterData = taF.some(DashboardAdapter.hasMetrics)
    var hasConvData  = convF.length > 0

    var stages = [
      { icon:'📤', name:'發布',   val:published,              na:false },
      { icon:'❤️', name:'互動',   val:hasInterData?totalInter:null, na:!hasInterData },
      { icon:'🔗', name:'連結點擊',val:null,                   na:true },
      { icon:'🌐', name:'進站',   val:null,                   na:true },
      { icon:'🎯', name:'轉換',   val:hasConvData?totalConv:null,   na:!hasConvData },
    ]
    var maxVal = stages.reduce(function(m,s){ return Math.max(m, s.na||s.val==null?0:s.val) },0) || 1

    var h = '<div class="db-sec"><div class="db-sec-title">轉換漏斗</div><div class="db-funnel-stages">'
    stages.forEach(function(s){
      var bw = (s.na||s.val==null) ? 0 : Math.max(4, Math.round(s.val/maxVal*100))
      h += '<div class="db-funnel-stage">'
         + '<span class="db-funnel-icon">'+s.icon+'</span>'
         + '<span class="db-funnel-name">'+s.name+'</span>'
         + '<div class="db-funnel-bar"><div class="db-funnel-fill" style="width:'+bw+'%"></div></div>'
         + '<span class="db-funnel-count">'
         + (s.na ? '<span class="db-funnel-na">尚未串接</span>' : (s.val!=null ? fmtNum(s.val) : '—'))
         + '</span></div>'
    })
    h += '</div><p class="db-funnel-hint">連結點擊、進站人數需串接 GA4 Worker 才可顯示</p></div>'
    return h
  }

  /* ---- 優化紀錄 (owner only) ---- */
  function buildOptLogSection() {
    var log = DashboardAdapter.optLog()
    var h = '<div class="db-sec db-owner-only"><div class="db-sec-title">優化紀錄</div>'
    if (!log.length) {
      h += '<div class="db-optlog-empty"><div class="db-optlog-icon">📋</div>'
         + '<div>尚無優化紀錄</div>'
         + '<div class="db-optlog-hint">可於此記錄策略調整、A/B 測試結果、改版前後對比</div></div>'
    } else {
      h += '<div style="overflow-x:auto"><table class="tbl" style="width:100%"><thead><tr>'
         + '<th>日期</th><th>項目</th><th>改動</th><th>結果</th></tr></thead><tbody>'
      log.forEach(function(row){
        h += '<tr><td>'+esc(row.date||'')+'</td><td>'+esc(row.item||'')+'</td>'
           + '<td>'+esc(row.change||'')+'</td><td>'+esc(row.result||'')+'</td></tr>'
      })
      h += '</tbody></table></div>'
    }
    return h + '</div>'
  }

  /* ---- 資料提醒 ---- */
  function buildAlertsSection(ta) {
    var alerts = []
    var now = todayStr()

    // 超過 3 天未補成效
    var cutoff = new Date(); cutoff.setDate(cutoff.getDate()-3)
    var cutoffStr = cutoff.toISOString().slice(0,10)
    var stale = ta.filter(function(a){
      var d = DashboardAdapter.dateOf(a)
      return d && d < cutoffStr && !DashboardAdapter.hasMetrics(a) && (a.notes||'').indexOf('貼文已刪除')===-1
    })
    if (stale.length) alerts.push({ icon:'⚠️', cls:'al-warn',
      text:'<strong>'+stale.length+' 則貼文</strong>超過 3 天未補成效',
      action:'→ 前往補填', link:'threadtracker' })

    // 近 7 日無發布
    var w7 = new Date(); w7.setDate(w7.getDate()-6)
    var w7Str = w7.toISOString().slice(0,10)
    var recent = ta.filter(function(a){ return DashboardAdapter.dateOf(a) >= w7Str })
    if (!recent.length) alerts.push({ icon:'📭', cls:'al-warn',
      text:'<strong>近 7 日無 Threads 發布紀錄</strong>',
      action:'→ 新增', link:'threadtracker' })

    // conv_daily 無資料
    if (!DashboardAdapter.convDaily().length) alerts.push({ icon:'ℹ️', cls:'al-info',
      text:'<strong>轉化紀錄</strong>尚未建立，漏斗資料不完整',
      action:'→ 前往記錄', link:'conv' })

    // 短連結監控（固定提示）
    alerts.push({ icon:'ℹ️', cls:'al-info',
      text:'<strong>連結點擊數</strong>尚未串接（需 GA4 Worker 或短連結 API）',
      action:'→ 成效總結', link:'ga4' })

    var h = '<div class="db-sec"><div class="db-sec-title">資料提醒</div><div class="db-alerts-list">'
    if (!alerts.length) {
      h += '<div class="db-alert-empty">✅ 目前無資料異常提醒</div>'
    } else {
      alerts.forEach(function(al){
        h += '<div class="db-alert '+al.cls+'" onclick="AppShell.navPage(\''+al.link+'\')">'
           + '<span class="db-alert-icon">'+al.icon+'</span>'
           + '<span class="db-alert-text">'+al.text+'</span>'
           + '<span class="db-alert-action">'+al.action+'</span>'
           + '</div>'
      })
    }
    return h + '</div></div>'
  }

})()
