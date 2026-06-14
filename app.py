"""
Watch It - LINE Bot 主程式

功能：
  - 接收 LINE Platform 的 Webhook 事件
  - 驗證 X-Line-Signature 簽章
  - 解析使用者指令並回覆對應訊息
"""

import logging
import sys

from flask import Flask, abort, request

# LINE Bot SDK v3（官方目前維護的版本，請勿使用已棄用的 linebot v2 模組）
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

from commands import dispatch_command, parse_command
from commands.database import init_db
from config import Config

# ---------------------------------------------------------------------------
# 日誌設定：方便在本機開發時追蹤 Webhook 請求與錯誤
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 啟動前驗證環境變數
# ---------------------------------------------------------------------------
Config.validate()

# 初始化 SQLite 資料表
init_db()

# ---------------------------------------------------------------------------
# Flask 應用程式初始化
# ---------------------------------------------------------------------------
app = Flask(__name__)

# LINE SDK v3 設定物件（Access Token 用於呼叫 Messaging API 回覆訊息）
line_configuration = Configuration(access_token=Config.LINE_CHANNEL_ACCESS_TOKEN)

# Webhook 事件解析器（Channel Secret 用於驗證請求簽章）
handler = WebhookHandler(Config.LINE_CHANNEL_SECRET)

# ---------------------------------------------------------------------------
# 排程器初始化 (加入 reloader 防護)
# ---------------------------------------------------------------------------
import os
import atexit
from commands.scheduler import start_scheduler, shutdown_scheduler

# 在 debug 模式下，Flask 會啟動主進程與 reloader 子進程。
# 檢查 WERKZEUG_RUN_MAIN 確保我們只在子進程（實際跑 app 的進程）啟動排程器，避免重複推播。
# 若非 debug 模式（例如正式機用 gunicorn），則直接啟動。
if not Config.FLASK_DEBUG or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    # 建立排程器專用的 ApiClient
    scheduler_api_client = ApiClient(line_configuration)
    scheduler_messaging_api = MessagingApi(scheduler_api_client)
    
    start_scheduler(scheduler_messaging_api, interval_minutes=5)
    
    # 註冊離開時的清理工作
    atexit.register(shutdown_scheduler)
    atexit.register(scheduler_api_client.close)




@app.route("/", methods=["GET"])
def health_check() -> tuple[str, int]:
    """
    健康檢查端點。

    可用於確認 Flask 伺服器是否正常運作（不經過 LINE 簽章驗證）。
    """
    return "Watch It LINE Bot is running.", 200


@app.route("/callback", methods=["POST"])
def callback() -> tuple[str, int]:
    """
    LINE Webhook 回呼端點。

    LINE Platform 會將使用者互動事件（訊息、加入好友等）以 POST 方式
    傳送到此 URL。我們必須：
      1. 讀取 X-Line-Signature 標頭
      2. 以 Channel Secret 驗證簽章
      3. 解析事件並交由 handler 分派處理

    Returns:
        成功時回傳 "OK" 與 HTTP 200（LINE 要求必須在時限內回應）。

    Raises:
        HTTP 400: 簽章驗證失敗。
        HTTP 500: 事件處理過程發生未預期錯誤。
    """
    # 取得 LINE 送來的簽章（用於驗證請求確實來自 LINE Platform）
    signature = request.headers.get("X-Line-Signature")
    if not signature:
        logger.warning("收到 Webhook 請求，但缺少 X-Line-Signature 標頭")
        abort(400, description="Missing X-Line-Signature header")

    # 以原始文字形式讀取 Request Body（簽章驗證必須使用未解析的原始 Body）
    body = request.get_data(as_text=True)
    logger.info("收到 Webhook 請求，Body 長度：%d 字元", len(body))

    try:
        # 解析 Webhook Body 並分派至對應的 @handler.add 裝飾器函式
        handler.handle(body, signature)
    except InvalidSignatureError:
        # 簽章不符：通常是 Channel Secret 設定錯誤，或請求並非來自 LINE
        logger.error(
            "簽章驗證失敗。請確認 .env 中的 LINE_CHANNEL_SECRET 是否正確。"
        )
        abort(400, description="Invalid signature")
    except Exception:
        # 非簽章錯誤仍回 200，避免 LINE 重送 Webhook 造成重複寫入
        logger.exception("處理 Webhook 事件時發生未預期錯誤")

    # LINE 要求 Webhook 端點必須回傳 HTTP 200 與 "OK"
    return "OK", 200


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event: MessageEvent) -> None:
    """
    文字訊息事件處理器。

    流程：原始文字 → 指令解析 → 分派處理 → 回覆使用者。

    Args:
        event: LINE Platform 傳來的 MessageEvent 物件。
    """
    user_text = event.message.text
    logger.info("收到文字訊息：%s", user_text)

    line_user_id = getattr(event.source, "user_id", None)

    try:
        if not line_user_id:
            reply_text = "❌ 無法取得使用者資訊，請以個人聊天方式使用本 Bot。"
        else:
            command = parse_command(user_text)
            reply_text = dispatch_command(command, line_user_id)
            logger.info("指令類型：%s", command.type.value)
    except Exception:
        logger.exception("處理訊息時發生未預期錯誤")
        reply_text = "❌ 系統發生錯誤，請稍後再試。"

    try:
        # 使用 ApiClient 上下文管理器，確保 HTTP 連線正確關閉
        with ApiClient(line_configuration) as api_client:
            messaging_api = MessagingApi(api_client)

            # 透過 Reply Message API 回覆（必須在收到事件的數秒內使用 reply_token）
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply_text)],
                )
            )
    except Exception:
        logger.exception("回覆 LINE 訊息失敗")

    logger.info("已回覆訊息")


if __name__ == "__main__":
    # 本機開發模式：直接執行 python app.py 啟動 Flask 內建伺服器
    # ngrok 會將公開 HTTPS URL 轉發到此埠號
    logger.info(
        "Watch It LINE Bot 啟動中 → http://%s:%s/callback",
        Config.FLASK_HOST,
        Config.FLASK_PORT,
    )
    app.run(
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT,
        debug=Config.FLASK_DEBUG,
    )
