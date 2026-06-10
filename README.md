# YS89 發文管理系統

社群發文 / 水軍管理 / GA4 成效 一站式後台。單頁應用（SPA），分頁切換，部署於 GitHub Pages。

線上：https://ysyyds0001-stack.github.io/ys89-system/

---

## 🗂 基礎設施速查（之後要找東西看這裡）

| 功能 | 在哪 | 後端 / 資料 | 怎麼更新 |
|---|---|---|---|
| **主系統（本 repo）** | `index.html` 單檔 SPA | LocalStorage + 選用同步 API | 改 `index.html` → push main → GitHub Pages 自動部署 |
| **GA4 成效分頁** | `index.html` 內 `#pg-ga4` 分頁 | 讀同 repo 的 `ga4-data.json` | 見下方「GA4 自動更新」 |
| **UTM 產生器分頁** | `index.html` 內 `#pg-utm` 分頁（iframe） | **不在本 repo**，見下方「UTM 產生器」 | 改 UTM 那個獨立專案後重新 deploy |

---

## 📊 GA4 自動更新

GA4 成效分頁的數據**不是寫死的**，是每天自動從 Google Analytics 4 拉取。

```
GitHub Actions（每天台灣 09:00）
  └─ ga4_fetch.py  ──讀──> GA4 Data API（property 539393762）
        │
        └─寫─> ga4-data.json ──commit──> GitHub Pages
                    │
                    └─ index.html 的 #pg-ga4 用 fetch('./ga4-data.json') 讀取渲染
```

- 排程設定：`.github/workflows/ga4-update.yml`
- 抓取腳本：`ga4_fetch.py`
- 憑證：GitHub repo secret **`GA4_SA_KEY`**（GA4 service account 金鑰，已設定）
- 測量 ID：`G-THDJFGXCZ7`（5 站共用）
- 本地手動跑一次：`GA4_SA_KEY_PATH=<金鑰路徑> python ga4_fetch.py`

> ⚠️ 已知待辦：CTA 轉換目前顯示 0，因為腳本用 `keyEvents` 指標，只計算「在 GA4 後台被標記為關鍵事件」的事件。需到 GA4 後台把註冊/LINE 點擊事件標記為關鍵事件，或把腳本改用 `eventCount`。

---

## 🏷️ UTM 產生器（重要：後端在別的地方）

UTM 產生器分頁（`#pg-utm`）是用 **iframe 嵌入一個獨立的 Cloudflare Pages 專案**，不是本 repo 的程式碼。

| 項目 | 位置 |
|---|---|
| **線上網址** | https://ys89-utm.pages.dev/ |
| **CF Pages 專案名** | `ys89-utm` |
| **CF 帳號** | ys89 主帳（`ysyyds1688@gmail.com`） |
| **前端 + 後端原始碼** | 桌面 `YS89-專案整理/UTM產生器/`（**不在本 repo**） |
| **後端 API** | CF Pages Functions：`functions/api/personas.js`、`functions/api/personas/[id].js` |
| **資料庫** | Cloudflare **D1**，名稱 `ys89-utm`，id `49ca2678-ed94-45d9-b2d5-63d588f4b2a7`（水軍名單共用，多人同步） |
| **D1 schema** | `UTM產生器/schema.sql` |

**怎麼更新 UTM 產生器：**
```bash
cd UTM產生器
# 改 index.html（前端）或 functions/（後端 API）
npx wrangler pages deploy . --project-name=ys89-utm
```

> 為什麼用 iframe 而不搬進本 repo：本 repo 是 GitHub Pages（純靜態，沒有後端 Functions），無法跑 `/api/personas` 那種 D1 後端。UTM 產生器需要共用 D1（多人同步水軍名單），所以留在 Cloudflare Pages，用 iframe 嵌入。兩邊都用同一個 ys89 CF 帳號，不需搬移。

---

## 🧭 分頁一覽

GA4 成效 · 發文角色 · 發文追蹤 · 文章庫 · 社群水軍號 · 炒話題追蹤 · Threads · 短連結 · UTM 產生器 · 入口 · 今日待辦 · 劇本
