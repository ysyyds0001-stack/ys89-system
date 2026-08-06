#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 YS89_帳號總表.xlsx 的 01_總表 轉成 D1 可匯入的 SQL。

總表是帳號資訊的唯一權威來源。改完總表跑這支重新產生，再用 wrangler 匯入：

    python 產生D1.py
    cd C:\\ys89\\d1
    npx wrangler d1 execute ys89-accounts --remote --file=accounts.sql

輸出的 SQL 開頭有 DROP TABLE，是整批覆蓋，不會殘留舊資料。
"""
import io
import os
import sys

import openpyxl

XLSX = os.environ.get("YS89_XLSX", r"C:\Users\haoli\Downloads\YS89_帳號總表.xlsx")
OUT = os.environ.get("YS89_D1_SQL", r"C:\ys89\d1\accounts.sql")
SHEET = "01_總表"

SCHEMA = """-- YS89 帳號主檔（權威來源：YS89_帳號總表.xlsx 01_總表）
-- 由 產生D1.py 自動產生，不要手改這份；總表更新後重新產生。
DROP TABLE IF EXISTS accounts;
CREATE TABLE accounts (
  account_id   TEXT PRIMARY KEY,   -- YS-IG-001
  persona_id   TEXT NOT NULL,      -- P-01
  name         TEXT NOT NULL,      -- 顯示名稱（權威）
  handle       TEXT,
  category     TEXT,
  platform     TEXT,
  disabled_platform TEXT,
  privacy      TEXT,
  status       TEXT,               -- 現役/觀察中/申訴中/已封存
  ig_followers INTEGER,
  th_followers INTEGER,
  domain       TEXT,
  post_mode    TEXT,               -- L1/L2/L3
  device       TEXT,
  slot         TEXT,
  node         TEXT,
  opened_at    TEXT,
  updated_at   TEXT,
  appeals      INTEGER,
  rebuild      TEXT,
  successor_id TEXT,
  note         TEXT,
  team         TEXT
);
CREATE INDEX idx_accounts_persona  ON accounts(persona_id);
CREATE INDEX idx_accounts_handle   ON accounts(handle);
CREATE INDEX idx_accounts_category ON accounts(category);
"""

COLS = ("account_id,persona_id,name,handle,category,platform,disabled_platform,privacy,status,"
        "ig_followers,th_followers,domain,post_mode,device,slot,node,opened_at,updated_at,"
        "appeals,rebuild,successor_id,note,team")

# 總表欄名 → 上面的欄位順序
FIELDS = ["帳號ID", "人設ID", "顯示名稱", "帳號 handle", "分類", "平台", "停用平台", "隱私",
          "狀態", "IG粉絲數", "TH粉絲數", "歸屬域名", "發文模式", "裝置", "登入槽位",
          "IP／節點", "開通日", "最後異動日", "申訴次數", "重建決議", "接班帳號ID",
          "備註", "經營組別"]
NUMERIC = {"IG粉絲數", "TH粉絲數", "申訴次數"}


def esc(s):
    return "'" + str(s if s is not None else "").replace("'", "''") + "'"


def num(v):
    """粉絲數欄位有 'X'、'—'、空白等非數字，一律轉 NULL 不要硬塞 0——
    0 的語意是「有量測，結果是零」，NULL 是「沒有資料」，混用會讓報表誤判。"""
    try:
        return str(int(float(str(v).replace(",", ""))))
    except (TypeError, ValueError):
        return "NULL"


def main():
    if not os.path.isfile(XLSX):
        print(f"找不到總表：{XLSX}", file=sys.stderr)
        return 1
    ws = openpyxl.load_workbook(XLSX, data_only=True)[SHEET]
    rows = list(ws.iter_rows(values_only=True))
    hi = next(i for i, r in enumerate(rows)
              if r and any(str(c or "").strip() == "帳號ID" for c in r))
    hdr = [str(c or "").strip() for c in rows[hi]]
    ix = {h: i for i, h in enumerate(hdr) if h}

    missing = [f for f in FIELDS if f not in ix]
    if missing:
        print(f"總表缺這些欄位，格式可能改過：{missing}", file=sys.stderr)
        return 1

    out = [SCHEMA]
    n = 0
    for r in rows[hi + 1:]:
        if not r or not r[ix["帳號ID"]]:
            continue
        vals = []
        for f in FIELDS:
            v = r[ix[f]]
            v = str(v).strip() if v is not None else ""
            vals.append(num(v) if f in NUMERIC else esc(v))
        out.append(f"INSERT INTO accounts ({COLS}) VALUES ({','.join(vals)});")
        n += 1

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print(f"已產生 {OUT}（{n} 筆）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
