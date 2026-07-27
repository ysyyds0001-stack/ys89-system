# CHANGELOG — YS89 社群管理系統 重構紀錄

> 本文件記錄 Phase 3 重構期間的所有主要變更（2026-07 起）。  
> 提交順序見 `git log --oneline`。

---

## 架構 / 導覽

- **Phase 3 全面重構**：五大分區 19 項頁面的 AppShell 側欄 + Topbar 導覽，取代舊式 nav-tab 列
- 新增 `assets/js/app-shell.js` + `assets/js/navigation-config.js`，與主檔案解耦
- Ctrl+K 全域快搜、Shift+\\ 側欄收合、行動裝置 drawer 模式
- 分頁重新命名：「社群平台炒群」→「社群互動」、「匿名社群發文」→「匿名社群」
- 新增獨立分頁：會議總覽、資料健康、數據輸入、Facebook、A/B Test

## 全域功能

- **全域日期選擇器**：Topbar 📅 widget，4 種快捷模式（本週/上週/近7天/近28天），持久化到 `localStorage('ys89_global_range')`，跨頁面同步 meeting/ga4 日期輸入
- 台北時區統一：新增 `getTaipeiDateString()` / `getTaipeiYesterday()` / `getTaipeiWeekStart()` 等工具函式，消除所有 `toISOString()` 錯誤日期

## 會議總覽頁（`meeting`）

- 10 KPI 卡片：發文數、曝光、點擊、GA4 Sessions、CTA Click、完成/有效/首存人數/首存金額
- **曝光 KPI 改為跨平台合計**：`Threads.views + IG.reach + FB.reach`，附各平台明細標注，移除「未含 IG/FB」警告
- 8 步轉換漏斗（社群曝光 → 首存）
- 平台成效表：Threads/IG/FB 各自曝光/觸及/讚數
- 帳號排行表：可按 5 欄點擊排序
- 列印/PDF 模式：自動隱藏操作按鈕、展開隱藏區塊
- `renderMsBizKpis()` 優先讀 v3 欄位名稱（`qualified_registration_count` / `first_deposit_user_count` / `first_deposit_amount`）

## 社群互動頁（`threadtracker`）

- **跨平台 metrics**：曝光/觸及、讚、互動欄位改為 Threads+IG+FB 三平台合計，日期分組小計同步更新
- 欄位標題：「曝光」→「曝光/觸及」、「留言」→「互動」
- 歸因等級徽章 (A/B/C/D/U) 顯示於 UTM 欄位下方
- 帳號健康 9 狀態矩陣 + openAddThreadActivity 重置新欄位
- `platformMetrics` 智慧合併：`DB.push` 防止空本機資料蓋掉 CF 成效；`DB.pull` 保留 CF 中的 `platformMetrics`
- Key 正規化：Python 寫入的 `threads`（小寫）→ JS 讀取的 `Threads`（大寫 T）migration

## 成效分析頁（`ga4`）

- 三層架構：成長概覽 / 成效分析 / 數據輸入
- `renderGrowthOverview()` 優先讀 v3 欄位名稱，fallback 舊 `reg/dep/amt`
- 成效分析時間線：`_ovDateRange` 讀 `_ga4Period`；`switchGA4Period` 呼叫 `renderGA4Overview`
- `_ovSetPeriod()` 改為同步 `globalRange`，避免雙重渲染

## 數據輸入頁（`datainput`）

- v3 schema 擴充：新增 `qualified_registration_count`、`first_deposit_user_count`、`first_deposit_count`、`first_deposit_amount`、`revenue_amount` 欄位
- 舊 `dep` 欄位遷移工具（一鍵升級存量資料）

## 文章庫（`articles`）

- 文章反向追查：每篇文章顯示「📌 N 篇引用」徽章
- `showArticleCitations()` 展示兩節：一般貼文引用 + 匿名鋪文引用

## 匿名社群頁（`channel`）

- 新增「引用文章庫」下拉選單（`cp-article` 欄位），支援 `articleId` 關聯
- `saveChannelPost()` 儲存 `articleId`
- `renderArticles()` 引用計數同時統計 `channel_posts`

## A/B Test 頁（`abtest`）

- 修正 DB key：`'ys89_ab_tests'` → `'ab_tests'`
- 修正欄位名稱：`t.start/t.end` → `t.startDate/t.endDate`
- 完整渲染：列表、勝出判斷（跨 UTM 引用 thread_activities）、導航至 GA4 管理按鈕

## 資料健康頁（`datahealth`）

- 14 項健康檢查（含短連結欄位、歸因一致性、時區正確性等）
- 短連結健康：修正欄位名稱（`originalUrl` / `shortLinkUrl`）

## 安全 / 個資

- 移除 `DEFAULT_ENTRANCES` 中的手機號碼與 email（體育專員 LINE 聯絡資訊）
- 移除 `DEFAULT_CONVERSIONS` handle 欄位中第三方使用者真實姓名（括號內中英文名，共 8 筆）

## 13 條行動建議升級

- 週行動建議從靜態規則升級至 13 條數據驅動規則，依 thread_activities 實際數據動態生成

## 內容詳情側抽屜

- `contentDetailClick()` + `openContentDetail()` — 點擊任何貼文/活動列開啟側抽屜，顯示完整 8 指標

---

*最後更新：2026-07-27*
