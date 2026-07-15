/* ============================================================
   YS89 App Shell — Phase 2 Navigation Refactor
   負責：側欄、Topbar、Ctrl+K 快搜、專案切換、模式切換
   不修改任何資料結構、localStorage key、頁面內部邏輯
   ============================================================ */

;(function () {
  'use strict'

  /* ---- 狀態 ---- */
  var _collapsed = false
  var _mode = 'operator'
  var _project = 'ys89'
  var _currentPage = ''
  var _qjResults = []
  var _qjSelected = 0

  /* ---- 讀/寫 localStorage ---- */
  var LS_KEY_SIDEBAR  = 'ys89_shell_sidebar_collapsed'
  var LS_KEY_MODE     = 'ys89_shell_mode'
  var LS_KEY_PROJECT  = 'ys89_shell_project'

  function lsGet(k) { try { return localStorage.getItem(k) } catch(e) { return null } }
  function lsSet(k, v) { try { localStorage.setItem(k, v) } catch(e) {} }

  /* ---- 取得目前頁面 ID ---- */
  function getInitialPage() {
    var active = document.querySelector('.page.active')
    return active ? active.id.replace('pg-', '') : 'multipost'
  }

  /* ---- 找出頁面所屬群組 label ---- */
  function getGroupForPage(pageId) {
    for (var gi = 0; gi < NAV_CONFIG.groups.length; gi++) {
      var g = NAV_CONFIG.groups[gi]
      for (var ii = 0; ii < g.items.length; ii++) {
        if (g.items[ii].page === pageId) return g.label
      }
    }
    return ''
  }

  /* ---- 找出頁面標籤 ---- */
  function getLabelForPage(pageId) {
    for (var gi = 0; gi < NAV_CONFIG.groups.length; gi++) {
      var items = NAV_CONFIG.groups[gi].items
      for (var ii = 0; ii < items.length; ii++) {
        if (items[ii].page === pageId) return items[ii].label
      }
    }
    var p = NAV_CONFIG.projects.find(function(x){ return x.page === pageId })
    return p ? p.label : pageId
  }

  /* ---- 更新 Topbar 頁面標題 ---- */
  function updateTopbarTitle(pageId) {
    var el = document.getElementById('app-tb-pagetitle')
    if (!el) return
    var label = getLabelForPage(pageId)
    var group = getGroupForPage(pageId)
    el.textContent = group ? (group + '  /  ' + label) : label
  }

  /* ---- 同步側欄 active ---- */
  function syncSidebarActive(pageId) {
    document.querySelectorAll('.sidebar-item').forEach(function(i) {
      i.classList.remove('active')
    })
    var el = document.querySelector('.sidebar-item[data-page="' + pageId + '"]')
    if (el) el.classList.add('active')
  }

  /* ---- 導航（Ctrl+K 或程式呼叫用） ---- */
  window.AppShell = {
    navPage: function(pageId) {
      if (!pageId) return
      var pgEl = document.getElementById('pg-' + pageId)
      if (!pgEl) { console.warn('[AppShell] page not found:', pageId); return }

      var sidebarItem = document.querySelector('.sidebar-item[data-page="' + pageId + '"]')
      if (sidebarItem) {
        nav(sidebarItem, pageId)
      } else {
        // 頁面在 project switcher（如 fortune）— 手動切換
        document.querySelectorAll('.page').forEach(function(p){ p.classList.remove('active') })
        document.querySelectorAll('.nav-tab').forEach(function(t){ t.classList.remove('active') })
        pgEl.classList.add('active')
        if (typeof fpInit === 'function' && pageId === 'fortune') fpInit()
      }

      _currentPage = pageId
      updateTopbarTitle(pageId)
      syncSidebarActive(pageId)
      closeQuickJump()

      // 手機：點選後關閉 drawer
      if (window.innerWidth <= 768) closeMobileSidebar()
    }
  }

  /* ---- 側欄 HTML ---- */
  function buildSidebarHTML() {
    var html = ''
    NAV_CONFIG.groups.forEach(function(g) {
      html += '<div class="sidebar-group">'
      html += '<div class="sidebar-group-label">' + g.label + '</div>'
      g.items.forEach(function(item) {
        html += '<div class="sidebar-item nav-tab" data-page="' + item.page
             + '" title="' + item.label + '"'
             + ' onclick="AppShell.navPage(\'' + item.page + '\')">'
             + '<span class="sidebar-item-icon">' + item.icon + '</span>'
             + '<span class="sidebar-item-label">' + item.label + '</span>'
             + '</div>'
      })
      html += '</div>'
    })
    html += '<div class="sidebar-spacer"></div>'
    return html
  }

  /* ---- Topbar HTML ---- */
  function buildTopbarHTML() {
    var modeItem = NAV_CONFIG.modes.find(function(m){ return m.id === _mode }) || NAV_CONFIG.modes[0]

    return '<button class="tb-toggle" id="app-tb-toggle" title="展開/收合側欄 (Shift+\\\\)">☰</button>'
         + '<div class="tb-brand">YS89<span>發文管理系統</span></div>'
         + '<div class="tb-page-title" id="app-tb-pagetitle"></div>'
         + '<button class="tb-mode-btn" id="app-tb-mode">'
         +   '<span id="app-tb-modeicon">' + modeItem.icon + '</span>'
         +   '<span id="app-tb-modelabel">' + modeItem.label + '</span>'
         + '</button>'
  }

  /* ---- 側欄收合 ---- */
  function toggleSidebar() {
    var isMobile = window.innerWidth <= 768

    if (isMobile) {
      // 手機：drawer 開關
      if (document.body.classList.contains('mobile-sidebar-open')) {
        closeMobileSidebar()
      } else {
        openMobileSidebar()
      }
      return
    }

    _collapsed = !_collapsed
    document.body.classList.toggle('sidebar-collapsed', _collapsed)
    lsSet(LS_KEY_SIDEBAR, _collapsed ? '1' : '0')
  }

  function closeMobileSidebar() {
    document.body.classList.remove('mobile-sidebar-open')
  }
  function openMobileSidebar() {
    document.body.classList.add('mobile-sidebar-open')
  }

  /* ---- 專案切換 ---- */
  function switchProject(projectId) {
    _project = projectId
    lsSet(LS_KEY_PROJECT, projectId)

    var proj = NAV_CONFIG.projects.find(function(p){ return p.id === projectId })
    if (!proj) return

    // 更新按鈕文字
    var iconEl  = document.querySelector('.tb-project-icon')
    var lblEl   = document.getElementById('app-tb-projlabel')
    if (iconEl) iconEl.textContent = proj.icon
    if (lblEl)  lblEl.textContent  = proj.label

    // 更新 dropdown active 樣式
    document.querySelectorAll('.tb-project-item').forEach(function(el) {
      el.classList.toggle('active', el.dataset.proj === projectId)
    })

    // 若專案有對應頁面，跳轉
    if (proj.page) {
      window.AppShell.navPage(proj.page)
    }

    closeProjectDropdown()

    if (typeof toast === 'function') {
      toast('切換專案：' + proj.label)
    }
  }

  function closeProjectDropdown() {
    var sw = document.getElementById('app-tb-project')
    if (sw) sw.classList.remove('open')
  }

  /* ---- 模式切換 ---- */
  function switchMode() {
    _mode = (_mode === 'operator') ? 'owner' : 'operator'
    lsSet(LS_KEY_MODE, _mode)

    var modeItem = NAV_CONFIG.modes.find(function(m){ return m.id === _mode })
    if (!modeItem) return

    var iconEl  = document.getElementById('app-tb-modeicon')
    var labelEl = document.getElementById('app-tb-modelabel')
    if (iconEl)  iconEl.textContent  = modeItem.icon
    if (labelEl) labelEl.textContent = modeItem.label

    document.body.classList.toggle('mode-owner', _mode === 'owner')

    if (typeof toast === 'function') {
      toast('切換模式：' + modeItem.label)
    }
  }

  /* ---- Quick Jump ---- */
  function openQuickJump() {
    var el = document.getElementById('app-quick-jump')
    if (!el) return
    el.classList.add('show')
    var input = document.getElementById('app-qj-input')
    if (input) { input.value = ''; input.focus() }
    renderQuickJumpResults('')
    _qjSelected = 0
  }

  function closeQuickJump() {
    var el = document.getElementById('app-quick-jump')
    if (el) el.classList.remove('show')
  }

  function renderQuickJumpResults(query) {
    _qjResults = []
    var q = query.toLowerCase().trim()

    NAV_CONFIG.groups.forEach(function(g) {
      g.items.forEach(function(item) {
        if (!q
            || item.label.toLowerCase().includes(q)
            || item.id.toLowerCase().includes(q)
            || (item.keywords && item.keywords.some(function(k){ return k.includes(q) }))) {
          _qjResults.push({ page: item.page, label: item.label, icon: item.icon, group: g.label })
        }
      })
    })

    // 專案頁面也加入搜尋
    NAV_CONFIG.projects.forEach(function(p) {
      if (p.page && (!q || p.label.toLowerCase().includes(q) || p.id.toLowerCase().includes(q))) {
        _qjResults.push({ page: p.page, label: p.label, icon: p.icon, group: '專案' })
      }
    })

    var listEl = document.getElementById('app-qj-results')
    if (!listEl) return

    if (_qjResults.length === 0) {
      listEl.innerHTML = '<div class="qj-empty">沒有符合的頁面</div>'
      return
    }

    listEl.innerHTML = _qjResults.map(function(item, i) {
      return '<div class="qj-result' + (i === 0 ? ' qj-selected' : '') + '" data-idx="' + i + '"'
           + ' onclick="AppShell.navPage(\'' + item.page + '\')">'
           + '<span class="qj-result-icon">' + item.icon + '</span>'
           + '<span>' + item.label + '</span>'
           + '<span class="qj-result-group">' + item.group + '</span>'
           + '</div>'
    }).join('')

    _qjSelected = 0
  }

  function qjMoveSelection(dir) {
    var items = document.querySelectorAll('.qj-result')
    if (!items.length) return
    items[_qjSelected].classList.remove('qj-selected')
    _qjSelected = (_qjSelected + dir + _qjResults.length) % _qjResults.length
    items[_qjSelected].classList.add('qj-selected')
    items[_qjSelected].scrollIntoView({ block: 'nearest' })
  }

  function qjConfirm() {
    if (_qjResults[_qjSelected]) {
      window.AppShell.navPage(_qjResults[_qjSelected].page)
    }
  }

  /* ---- 快捷鍵 ---- */
  function bindKeys() {
    document.addEventListener('keydown', function(e) {
      // Ctrl+K 或 Cmd+K 開啟快搜
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault()
        openQuickJump()
        return
      }

      var qjOpen = document.getElementById('app-quick-jump')?.classList.contains('show')

      if (qjOpen) {
        if (e.key === 'Escape')    { e.preventDefault(); closeQuickJump() }
        if (e.key === 'ArrowDown') { e.preventDefault(); qjMoveSelection(1) }
        if (e.key === 'ArrowUp')   { e.preventDefault(); qjMoveSelection(-1) }
        if (e.key === 'Enter')     { e.preventDefault(); qjConfirm() }
        return
      }

      // Shift+\ (Shift+Backslash) 切換側欄
      if (e.shiftKey && e.key === '\\') { toggleSidebar() }
    })
  }

  /* ---- 建立 DOM ---- */
  function buildDOM() {
    // Topbar
    var topbar = document.createElement('div')
    topbar.id = 'app-topbar'
    topbar.innerHTML = buildTopbarHTML()
    document.body.insertBefore(topbar, document.body.firstChild)

    // Sidebar
    var sidebar = document.createElement('div')
    sidebar.id = 'app-sidebar'
    sidebar.innerHTML = buildSidebarHTML()
    document.body.insertBefore(sidebar, document.body.firstChild)

    // Mobile sidebar overlay
    var overlay = document.createElement('div')
    overlay.id = 'app-sidebar-overlay'
    overlay.onclick = closeMobileSidebar
    document.body.insertBefore(overlay, document.body.firstChild)

    // Quick Jump 浮層
    var qj = document.createElement('div')
    qj.id = 'app-quick-jump'
    qj.innerHTML = '<div class="qj-modal">'
                 + '<div class="qj-search-wrap">'
                 +   '<span class="qj-search-icon">🔍</span>'
                 +   '<input id="app-qj-input" placeholder="搜尋頁面…" autocomplete="off">'
                 +   '<span class="qj-hint"><kbd>↑↓</kbd> 選擇  <kbd>↵</kbd> 前往  <kbd>Esc</kbd> 關閉</span>'
                 + '</div>'
                 + '<div id="app-qj-results"></div>'
                 + '</div>'
    document.body.appendChild(qj)
    qj.addEventListener('click', function(e) {
      if (e.target === qj) closeQuickJump()
    })
  }

  /* ---- 綁定 Topbar 事件 ---- */
  function bindTopbar() {
    document.getElementById('app-tb-toggle').addEventListener('click', toggleSidebar)
    document.getElementById('app-tb-mode').addEventListener('click', switchMode)
    document.getElementById('app-qj-input').addEventListener('input', function() {
      renderQuickJumpResults(this.value)
      _qjSelected = 0
    })
  }

  /* ---- 初始化 ---- */
  function init() {
    // 讀取 localStorage 狀態
    _collapsed = lsGet(LS_KEY_SIDEBAR) === '1'
    _mode      = lsGet(LS_KEY_MODE)    || 'operator'
    _project   = lsGet(LS_KEY_PROJECT) || 'ys89'

    // 建立 DOM
    buildDOM()
    bindTopbar()
    bindKeys()

    // 套用 body classes
    document.body.classList.add('app-shell-active')
    if (_collapsed) document.body.classList.add('sidebar-collapsed')
    if (_mode === 'owner') document.body.classList.add('mode-owner')

    // 偵測目前頁面並同步側欄 + topbar
    _currentPage = getInitialPage()
    syncSidebarActive(_currentPage)
    updateTopbarTitle(_currentPage)

    // 舊 nav 加上 legacy class（讓 CSS 隱藏）
    var oldNav = document.querySelector('nav:not(#app-topbar)')
    if (oldNav && !oldNav.id) oldNav.classList.add('legacy-navigation')
  }

  /* ---- 等 DOM + 既有 JS 就緒後再啟動 ---- */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init)
  } else {
    // 延一個 tick，確保 index.html 的 IIFE 先跑
    setTimeout(init, 0)
  }

})()
