# YS89 Navigation Refactor — Phase 2 完成報告

完成時間：2026-07-15  
分支：`refactor/navigation-shell`

---

## 一、本次改動摘要

### 新增檔案
| 檔案 | 大小 | 說明 |
|---|---|---|
| `assets/js/navigation-config.js` | ~2 KB | 集中式導覽設定（6 個群組、16 頁、2 模式、2 專案） |
| `assets/css/app-shell.css` | ~7 KB | 側欄、Topbar、快搜浮層、RWD 樣式 |
| `assets/js/app-shell.js` | ~8 KB | App Shell 邏輯（側欄收合、專案切換、模式切換、Ctrl+K） |

### 修改檔案（僅 4 行差異）
| 位置 | 修改內容 |
|---|---|
| `index.html` 第 285 行 | `<head>` 尾端加入 CSS `<link>` |
| `index.html` 第 289 行 | `<nav>` 加上 `class="legacy-navigation"` |
| `index.html` 第 11087–11088 行 | `</body>` 前加入 2 個 `<script>` |

---

## 二、新版導覽架構

### 側欄 6 個群組
| 群組 | 頁面（page ID） |
|---|---|
| 工作台 | multipost（多平台發文）、todo（今日待辦） |
| 發布管理 | threadtracker、channel、channelfb、tracker |
| 內容資產 | articles、cast、community |
| 成效與轉換 | ga4、conv |
| 行銷工具 | utm、links、entrances |
| 系統設定 | guide |

### 專案切換器（框架）
- YS89 夜色（預設）
- 財神預測 → 點選後導向 `pg-fortune`

---

## 三、功能說明

### Topbar（固定頂部，52px）
- 左：☰ 漢堡按鈕（收合/展開側欄）
- 左中：品牌名 YS89 發文管理系統
- 中左：專案切換器下拉選單
- 中：目前頁面路徑（群組 / 頁面名稱）
- 右：模式切換按鈕（操盤手 / 業主報告）

### 側欄（固定左側）
- 展開寬度：240px
- 收合寬度：64px（僅顯示 emoji 圖示，`title` attribute 提供 tooltip）
- 過渡動畫：0.22s ease
- Active 指示：左側 2px 橘紅色邊框 + 淡底色

### Ctrl+K 快搜
- 觸發：Ctrl+K（Windows/Linux）或 Cmd+K（Mac）
- 支援：頁面名稱、ID、關鍵字搜尋（含注音相關詞）
- 鍵盤導航：↑↓ 移動選項，Enter 確認，Esc 關閉

### 側欄收合快捷鍵
- Shift+\（反斜線）切換側欄展開/收合

### 狀態持久化（localStorage）
| Key | 說明 |
|---|---|
| `ys89_shell_sidebar_collapsed` | 側欄收合狀態 |
| `ys89_shell_mode` | 模式（operator / owner） |
| `ys89_shell_project` | 目前專案 |

---

## 四、保留清單（完全未動）

- ✅ 所有 `.page` / `pg-*` 頁面內容
- ✅ `nav()` 函式邏輯與 `renderXxx()` 呼叫
- ✅ `DB` 類別與全部 30 個 localStorage key
- ✅ `posts`、`thread_activities`、`channel_posts` 資料結構
- ✅ 全部 modal（`openModal` / `closeModal`）
- ✅ Telegram Bot、GA4 Worker、Python Server 整合
- ✅ `picks168.com API key`（僅存於 dashboard_server.py）
- ✅ 舊 `<nav>` 元素（只加 class `legacy-navigation`，CSS 隱藏；移除新版後還原一行即可）

---

## 五、新舊並存機制

舊導覽列（`<nav class="legacy-navigation">`）被 CSS `display: none !important` 隱藏，但元素仍在 DOM 中。  
恢復舊版只需兩步：
1. 移除 `index.html` 第 285 行的 CSS `<link>`
2. 移除第 11087–11088 行兩個 `<script>`

---

## 六、已知限制（本階段）

- 「業主報告」模式目前只更新 Topbar 視覺標記，尚未限制頁面內容（按規格，本階段只建框架）
- 「專案切換器」不過濾任何現有資料（按規格）
- 財神預測（pg-fortune）透過 Project Switcher 進入，側欄不顯示

---

## 七、下一步建議

1. 提交 `refactor/navigation-shell` 分支，發起 PR 合回 main
2. Phase 3：「業主報告」模式實作（隱藏操作欄、僅顯示 KPI 摘要）
3. 可選：側欄加入 Threads / GA4 今日數字小卡（widget）
