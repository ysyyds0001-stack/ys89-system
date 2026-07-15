/* YS89 Navigation Config — Phase 2 App Shell */
/* 只做分類對應；不修改任何資料結構、localStorage key、頁面內部邏輯 */

const NAV_CONFIG = {
  groups: [
    {
      id: 'workbench',
      label: '工作台',
      items: [
        { id: 'dashboard',     label: '儀表板',       icon: '📊', page: 'dashboard',     keywords: ['儀表板','dashboard','總覽','kpi'] }
      ]
    },
    {
      id: 'publishing',
      label: '發布管理',
      items: [
        { id: 'multipost',     label: '多平台發文',   icon: '📡', page: 'multipost',     keywords: ['發文','多平台','post'] },
        { id: 'threadtracker', label: '社群炒群',     icon: '🔥', page: 'threadtracker', keywords: ['炒群','社群','threads','ig','fb'] },
        { id: 'channel',       label: '匿名社群',     icon: '📝', page: 'channel',       keywords: ['匿名','頻道','anon'] },
        { id: 'channelfb',     label: 'Facebook社團', icon: '📘', page: 'channelfb',     keywords: ['fb','facebook','社團'] },
        { id: 'tracker',       label: '發文追蹤',     icon: '📈', page: 'tracker',       keywords: ['追蹤','tracker','紀錄'] }
      ]
    },
    {
      id: 'content',
      label: '內容資產',
      items: [
        { id: 'articles',      label: '文章庫',       icon: '📚', page: 'articles',      keywords: ['文章','article'] },
        { id: 'community',     label: '角色管理',     icon: '👤', page: 'community',     keywords: ['角色','persona','帳號'] }
      ]
    },
    {
      id: 'analytics',
      label: '成效與轉換',
      items: [
        { id: 'ga4',           label: '成效總結',     icon: '📊', page: 'ga4',           keywords: ['成效','ga4','分析','報告'] },
        { id: 'conv',          label: '轉化區',       icon: '💰', page: 'conv',          keywords: ['轉化','conv','登記','詢問','儲值'] }
      ]
    },
    {
      id: 'tools',
      label: '行銷工具',
      items: [
        { id: 'utm',           label: 'UTM 產生器',   icon: '🏷️', page: 'utm',           keywords: ['utm','產生器','追蹤碼'] },
        { id: 'links',         label: '短連結',       icon: '🔗', page: 'links',         keywords: ['短連結','link'] },
        { id: 'entrances',     label: '導流入口',     icon: '🚪', page: 'entrances',     keywords: ['入口','導流','entrance'] }
      ]
    },
    {
      id: 'settings',
      label: '系統設定',
      items: [
        { id: 'guide',         label: '使用說明',     icon: '📖', page: 'guide',         keywords: ['說明','guide','幫助','help'] }
      ]
    }
  ],

  projects: [],

  /* 模式切換 — 本階段只顯示狀態標記，不改變功能 */
  modes: [
    { id: 'operator', label: '操盤手', icon: '⚡' },
    { id: 'owner',    label: '業主報告', icon: '👔' }
  ]
}
