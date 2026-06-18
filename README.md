# Watch It —— 台股觸價警示 LINE Bot

Watch It 是一個以 LINE 為操作介面的台股盯盤機器人。使用者透過 LINE 對話即可管理自選股清單、設定價格警示，系統在交易時段定時監控股價，當股價觸及設定條件時主動推播通知。

本專案為 Python 程式設計課程個人專題，採 AI 輔助開發（Vibe Coding）流程完成，全程以模組化架構、資料持久化、完整錯誤處理與單元測試為核心要求。

---

## 功能特色

- **自選股管理**：透過 LINE 指令新增、查詢、刪除自選股票。
- **觸價警示**：對自選股設定「高於 / 低於」目標價的警示條件，支援新增、查詢、修改、刪除與清空。
- **自動推播**：背景排程器定時檢查股價，條件達成時主動推播通知，並標記已觸發避免重複通知。
- **交易時段判斷**：僅在台股交易時段（週一至週五 09:00–13:30）執行查價，非交易時段自動略過。
- **資料時效標註**：盤後或休市時取得的股價會標記為「非即時報價」，誠實提示使用者。
- **快速回覆按鈕**：常用操作提供 LINE Quick Reply 按鈕，減少手動輸入。
- **輸入防呆**：支援全形數字轉換、彈性空格辨識，並對非法輸入提供友善提示。

---

## 技術架構

本專案整合四個技術領域：**Web 框架、資料庫、第三方 API、背景排程**。

| 層級 | 模組 | 說明 |
|------|------|------|
| 入口 | `app.py` | Flask 應用、LINE Webhook 簽章驗證、排程器啟動 |
| 指令解析 | `commands/parser.py`、`commands/models.py` | 指令正規化與解析、防呆驗證 |
| 指令分派 | `commands/handlers.py` | 將解析後指令分派至對應服務，組裝回覆與 Quick Reply |
| 資料層 | `commands/database.py`、`commands/db_models.py` | SQLAlchemy 2.0 ORM、SQLite、session 管理 |
| 服務層 | `commands/watch_service.py`、`commands/alert_service.py` | 自選股與警示的 CRUD 邏輯 |
| 股價 | `commands/price_fetcher.py`、`commands/market_hours.py` | 股價抓取（含逾時與降級）、交易時段判斷 |
| 推播與排程 | `commands/notifier.py`、`commands/scheduler.py` | 主動推播、APScheduler 背景排程與條件比對 |

### 技術棧

- Python 3.10+
- Flask 3.1（Web 框架）
- line-bot-sdk 3.23（LINE Messaging API v3）
- SQLAlchemy 2.0 + SQLite（資料持久化）
- twstock 1.5（台股股價）
- APScheduler 3.10（背景排程）
- pytest（單元測試）

---

## 端到端流程

```
使用者於 LINE 設定警示
        ↓
指令解析 → 寫入 SQLite
        ↓
背景排程每 5 分鐘檢查（判斷是否為交易時段）
        ↓
抓取即時股價 → 比對警示條件
        ↓
條件達成 → 主動推播 LINE 通知 → 標記為已觸發
```

---

## 安裝與執行

### 1. 取得專案與安裝套件

```bash
git clone https://github.com/kairos170e/WatchIt.git
cd WatchIt
python -m venv .venv
# Windows
.\.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. 設定環境變數

複製範本並填入你自己的 LINE 憑證（於 [LINE Developers Console](https://developers.line.biz/console/) 取得）：

```bash
cp .env.example .env
```

編輯 `.env`：

```env
LINE_CHANNEL_ACCESS_TOKEN=你的_Channel_Access_Token
LINE_CHANNEL_SECRET=你的_Channel_Secret
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_DEBUG=False
```

### 3. 啟動服務

```bash
python app.py
```

### 4. 以 ngrok 建立公開連線並設定 Webhook

```bash
ngrok http 5000
```

將 ngrok 提供的 HTTPS 網址加上 `/callback`（例如 `https://xxxx.ngrok-free.app/callback`）填入 LINE Developers Console 的 Webhook URL，啟用 Use webhook，並關閉自動回覆。

---

## 使用方式（LINE 指令）

| 指令 | 功能 |
|------|------|
| `加自選 2330` | 將台積電加入自選股 |
| `自選` | 查看自選股清單 |
| `刪自選 2330` | 從自選股移除 |
| `警示 2330 > 1000` | 設定「台積電高於 1000」警示 |
| `警示清單` | 查看所有警示 |
| `改警示 1 < 950` | 修改第 1 筆警示 |
| `刪警示 1` | 刪除第 1 筆警示 |
| `清空警示` | 清空全部警示（需二次確認） |
| `2330` 或 `查詢 2330` | 查詢目前股價 |
| `幫助` | 顯示使用說明 |

---

## 測試

專案包含 67 項單元測試，涵蓋指令解析、CRUD、交易時段判斷、股價降級邏輯、警示比對與推播。測試使用 in-memory SQLite 與 mock，不依賴真實網路或資料庫。

```bash
pytest tests/ -v
```

---

## 設計重點

- **金額精度**：所有價格使用 `Decimal` / SQLAlchemy `Numeric`，避免浮點誤差。
- **防重複通知**：警示觸發採「推播成功才標記」策略，推播失敗則下一輪重試。
- **防重複排程**：Flask debug 模式下透過 `WERKZEUG_RUN_MAIN` 確保排程器僅啟動一次。
- **資料安全**：LINE 憑證透過環境變數載入，`.env` 已排除於版本控制之外。

---

## 授權

本專案為課程作業用途。
