# YS89 儀表板 v1 — 完成報告

完成時間：2026-07-15
分支：`main`

---

## 一、變更摘要

### 新增檔案

| 檔案 | 大小 | 說明 |
|---|---|---|
| `assets/js/dashboard-adapter.js` | ~3 KB | 資料讀取層，純唯讀，不修改任何既有結構 |
| `assets/css/dashboard.css` | ~8 KB | 儀表板專屬樣式（KPI 卡、趨勢圖、漏斗、提醒） |
| `assets/js/dashboard.js` | ~12 KB | 儀表板渲染邏輯（9 個 section builder） |
| `docs/dashboard-v1-report.md` | — | 本報告 |

### 修改檔案

| 檔案 | 修改內容 |
|---|---|
| `index.html` | 加入 CSS link、新增 `pg-dashboard` div（設為 active 預設頁）、移除 `pg-multipost` 的 active class、移除舊 nav 的 todo 入口、加入 3 個 `<script>` 標籤 |
| `navigation-config.js` | 工作台群組改為只含「儀表板」；發布管理加入「多平台發文」為第一項 |
| `app-shell.js` | `navPage()` 加入 dashboard render hook；`init()` 加入初始頁面為 dashboard 時的 render 呼叫 |

---

## 二、導覽架構變更

### 工作台群組（工作台）
| 前 | 後 |
|---|---|
| 多平台發文、今日待辦 | 儀表板（唯一項目） |

### 發布管理群組
| 前 | 後 |
|---|---|
| 社群炒群、匿名社群、Facebook社團、發文追蹤 | **多平台發文**（移入）、社群炒群、匿名社群、Facebook社團、發文追蹤 |

### 今日待辦
- 導覽入口已移除（側欄、舊 nav、Ctrl+K 均不顯示）
- `pg-todo` HTML、`renderTodo()`、`initTodayTodos()`、`daily_todos` localStorage key **完整保留**
- 恢復方法：在 `navigation-config.js` 的工作台 items 加回 `{ id:'todo', label:'今日待辦', icon:'📋', page:'todo', keywords:['待辦','任務','todo'] }`

---

## 三、儀表板頁面結構（9 個 Section）

| # | Section | 資料來源 | 可用性 |
|---|---|---|---|
| 1 | **核心指標（6 KPI）** | thread_activities、posts、channel_posts、conv_daily | 部分可計算 |
| 2 | **今日概況** | thread_activities（今日） | 可計算・operator 模式限定 |
| 3 | **成效趨勢** | thread_activities（每日發布數 / 互動數） | 可計算 |
| 4 | **平台與角色表現** | thread_activities（按 platform / persona 分組） | 可計算 |
| 5 | **最佳與待優化內容** | thread_activities（按互動數排序） | 可計算 |
| 6 | **轉換漏斗** | thread_activities + conv_daily；連結點擊/進站顯示「尚未串接」 | 部分可計算 |
| 7 | **優化紀錄** | `ys89_dashboard_optlog`（新 key，預設空陣列） | owner 模式限定 |
| 8 | **資料提醒** | thread_activities（超過 3 天未補成效、近 7 日無發布等） | 可計算 |

---

## 四、資料 Adapter 說明

### 資料來源對應表

| KPI | 資料來源 | 欄位 | 說明 |
|---|---|---|---|
| 本期發布數 | thread_activities + posts + channel_posts | count | 三個來源各自計算後加總，分開標示 |
| 待補成效 | thread_activities | hasMetrics() | notes 含「貼文已刪除」者排除 |
| 總互動 | thread_activities | likes + replies/comments + reposts | 相容兩種欄位格式 |
| 連結點擊 | — | — | **尚未串接**（需 GA4 Worker） |
| 完成轉換 | conv_daily | inq + reg + dep | 無資料顯示「—」 |
| 資料完整率 | thread_activities | hasMetrics() / total | 排除已刪除貼文 |

### 欄位相容設計

`DashboardAdapter.getMetrics(entry)` 同時支援：
- 扁平格式：`entry.views`, `entry.likes`, `entry.replies`
- 巢狀格式：`entry.metrics.views`, `entry.metrics.likes`, `entry.metrics.replies`

---

## 五、模式差異（操盤手 vs 業主報告）

| Section | 操盤手 | 業主報告 |
|---|---|---|
| 核心指標 | ✅ | ✅ |
| 今日概況 + 快速操作 | ✅ | ❌（`.db-operator-only`） |
| 成效趨勢 | ✅ | ✅ |
| 平台與角色表現 | ✅ | ✅ |
| 最佳與待優化內容 | ✅ | ✅ |
| 轉換漏斗 | ✅ | ✅ |
| 優化紀錄 | ❌（`.db-owner-only`） | ✅ |
| 資料提醒 | ✅ | ✅ |

---

## 六、安全規則遵守確認

| 規則 | 執行狀態 |
|---|---|
| 先只移除「今日待辦」的導覽入口 | ✅ 只移除 nav 入口，pg-todo 保留 |
| 不刪除今日待辦的 HTML、JS、localStorage | ✅ 完全保留 |
| 保留還原方式 | ✅ 一行 navigation-config.js 即可恢復 |
| 不修改 posts、thread_activities、channel_posts 資料結構 | ✅ Adapter 純唯讀 |
| 不為缺少的數據建立假數字 | ✅ 無資料顯示「—」或「尚未串接」 |
| 不將無資料顯示為 0 | ✅ 以 null 區分「未填」與「填了 0」 |
| 不重寫整個 index.html | ✅ 只增加 5 行 |
| 不修改其他頁面的新增、編輯、刪除與儲存功能 | ✅ dashboard.js 只讀取資料，不修改 |

---

## 七、新增 localStorage Key

| Key | 說明 | 影響 |
|---|---|---|
| `ys89_dashboard_optlog` | 優化紀錄（新增；預設空陣列） | 不影響任何現有功能 |

---

## 八、技術限制（已知）

1. **連結點擊、進站人數**：需串接 GA4 Worker，目前顯示「尚未串接」
2. **趨勢圖**：純 CSS div 實作，無動畫；可替換為 Chart.js 而不影響其他部分
3. **角色列表**：從 `thread_activities` 動態提取，若 `personas` 表與 `thread_activities.persona` 欄位值不一致，篩選器以 `thread_activities` 為準
4. **posts / channel_posts 欄位**：因欄位結構不明確，「本期發布數」只計 count，不計算這兩個來源的成效（互動數僅來自 thread_activities）

---

## 九、下一步建議

1. **串接 GA4 Worker**：取得連結點擊、進站人數後補入漏斗第 3、4 階
2. **串接 conv_daily**：若尚未建立轉化紀錄，前往轉化區填入 inq/reg/dep
3. **補完 posts / channel_posts 欄位說明**：確認欄位格式後，將兩個來源的互動數也納入 KPI
4. **優化紀錄**：設計一個簡單的新增表單（date / item / change / result）
5. **Ctrl+K 快搜**：dashboard 已加入 keywords（儀表板、kpi、總覽），可直接用快搜導航

---

## 十、檔案清單

```
新增:
  assets/js/dashboard-adapter.js
  assets/css/dashboard.css
  assets/js/dashboard.js
  docs/dashboard-v1-report.md

修改:
  index.html                         (+8 行 / -1 行)
  assets/js/navigation-config.js    (重構工作台群組、擴展發布管理)
  assets/js/app-shell.js            (+8 行，dashboard render hook)
```
