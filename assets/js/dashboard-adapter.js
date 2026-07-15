/* ============================================================
   YS89 Dashboard Data Adapter — v1
   讀取既有 localStorage 資料，不修改任何原始資料結構
   三個主要來源：thread_activities / posts / channel_posts
   ============================================================ */

var DashboardAdapter = (function () {
  'use strict'

  function dbGet(k) {
    try {
      if (typeof DB !== 'undefined' && typeof DB.get === 'function') return DB.get(k)
      return JSON.parse(localStorage.getItem('ys89_' + k) || 'null')
    } catch (e) { return null }
  }

  function safe(v) { return Array.isArray(v) ? v : [] }

  function dateOf(entry) {
    return (entry.date || entry.created_at || entry.timestamp || '').slice(0, 10)
  }

  function filterByDate(arr, start, end) {
    if (!start && !end) return arr
    return arr.filter(function (item) {
      var d = dateOf(item)
      return d >= start && d <= end
    })
  }

  // 相容「欄位直接在 entry 上」與「欄位在 entry.metrics 子物件」兩種格式
  function getMetrics(entry) {
    var m = (entry && entry.metrics && typeof entry.metrics === 'object') ? entry.metrics : entry
    return {
      views:   (m && m.views   != null) ? +m.views   : null,
      likes:   (m && m.likes   != null) ? +m.likes   : null,
      cmts:    (m && m.replies != null) ? +m.replies :
               (m && m.comments!= null) ? +m.comments : null,
      shares:  (m && m.reposts != null) ? +m.reposts :
               (m && m.shares  != null) ? +m.shares  : null,
      saves:   (m && m.saves   != null) ? +m.saves   : null,
      follows: (m && m.follows != null) ? +m.follows : null,
    }
  }

  function hasMetrics(entry) {
    if ((entry.notes || '').indexOf('貼文已刪除') !== -1) return false
    var m = getMetrics(entry)
    return m.views != null || m.likes != null
  }

  function getDateRange(rangeKey, customStart, customEnd) {
    var today = new Date()
    var fmt = function (d) { return d.toISOString().slice(0, 10) }
    var end = fmt(today)
    var start
    if (rangeKey === 'today') {
      start = end
    } else if (rangeKey === '30d') {
      var s = new Date(today); s.setDate(s.getDate() - 29); start = fmt(s)
    } else if (rangeKey === 'custom') {
      start = customStart || end; end = customEnd || end
    } else {
      var s2 = new Date(today); s2.setDate(s2.getDate() - 6); start = fmt(s2)
    }
    return { start: start, end: end }
  }

  return {
    getDateRange:     getDateRange,
    filterByDate:     filterByDate,
    getMetrics:       getMetrics,
    hasMetrics:       hasMetrics,
    dateOf:           dateOf,

    threadActivities: function () { return safe(dbGet('thread_activities')) },
    posts:            function () { return safe(dbGet('posts')) },
    channelPosts:     function () { return safe(dbGet('channel_posts')) },
    convDaily:        function () { return safe(dbGet('conv_daily')) },
    personas:         function () { return safe(dbGet('personas')) },
    links:            function () { return safe(dbGet('links')) },
    dailyTodos:       function () { return safe(dbGet('daily_todos')) },
    optLog:           function () { return safe(dbGet('dashboard_optlog')) },
    saveOptLog:       function (arr) {
      try {
        if (typeof DB !== 'undefined' && typeof DB.set === 'function') DB.set('dashboard_optlog', arr)
        else localStorage.setItem('ys89_dashboard_optlog', JSON.stringify(arr))
      } catch (e) {}
    }
  }
})()
