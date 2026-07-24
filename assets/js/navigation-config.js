/* YS89 Navigation Config — Phase 3 Meeting-First Refactor */
/* 只做分類對應；不修改任何資料結構、localStorage key、頁面內部邏輯 */

const NAV_CONFIG = {
  groups: [
    {
      id: 'analysis',
      label: '會議與分析',
      items: [
        { id: 'meeting',    label: '會議總覽',   icon: '📋', page: 'meeting',    keywords: ['會議','報告','總覽','meeting','report','kpi'] },
        { id: 'ga4',        label: '成效分析',   icon: '📊', page: 'ga4',        keywords: ['成效','ga4','分析','報告','overview'] },
        { id: 'datahealth', label: '資料健康',   icon: '🔍', page: 'datahealth', keywords: ['資料','健康','data','health','品質','audit'] }
      ]
    },
    {
      id: 'publishing',
      label: '內容與執行',
      items: [
        { id: 'tracker',       label: '發文追蹤',   icon: '📈', page: 'tracker',       keywords: ['追蹤','tracker','紀錄'] },
        { id: 'threadtracker', label: '社群互動',   icon: '🔥', page: 'threadtracker', keywords: ['炒群','社群','threads','ig','fb'] },
        { id: 'channel',       label: '匿名社群',   icon: '📝', page: 'channel',       keywords: ['匿名','頻道','anon'] },
        { id: 'channelfb',     label: 'Facebook',   icon: '📘', page: 'channelfb',     keywords: ['fb','facebook','社團'] },
        { id: 'conv',          label: '轉化型內容', icon: '🎯', page: 'conv',          keywords: ['轉化','conv','登記','詢問','儲值'] },
        { id: 'multipost',     label: '多平台發文', icon: '📡', page: 'multipost',     keywords: ['發文','多平台','post'] }
      ]
    },
    {
      id: 'content',
      label: '內容資產',
      items: [
        { id: 'community',  label: '角色',       icon: '👤', page: 'community',  keywords: ['角色','persona','帳號'] },
        { id: 'articles',   label: '文章庫',     icon: '📚', page: 'articles',   keywords: ['文章','article'] },
        { id: 'templates',  label: '文案模板庫', icon: '🧩', page: 'templates',  keywords: ['模板','template','文案','結構'] }
      ]
    },
    {
      id: 'tools',
      label: '追蹤工具',
      items: [
        { id: 'utm',      label: 'UTM 產生器', icon: '🏷️', page: 'utm',      keywords: ['utm','產生器','追蹤碼'] },
        { id: 'links',    label: '短連結',     icon: '🔗', page: 'links',    keywords: ['短連結','link'] },
        { id: 'entrances',label: '入口管理',   icon: '🚪', page: 'entrances',keywords: ['入口','導流','entrance'] },
        { id: 'abtest',   label: 'A/B Test',   icon: '🧪', page: 'abtest',   keywords: ['ab','test','測試','abtest'] }
      ]
    },
    {
      id: 'settings',
      label: '管理',
      items: [
        { id: 'datainput', label: '數據輸入', icon: '✏️', page: 'datainput', keywords: ['輸入','data','input','manual','手動'] },
        { id: 'dashboard', label: '系統設定', icon: '⚙️', page: 'dashboard', keywords: ['儀表板','dashboard','設定','config'] },
        { id: 'guide',     label: '使用說明', icon: '📖', page: 'guide',     keywords: ['說明','guide','幫助','help'] }
      ]
    }
  ],

  projects: [],

  modes: [
    { id: 'operator', label: '操盤手', icon: '⚡' },
    { id: 'meeting',  label: '會議模式', icon: '📋' }
  ]
}
