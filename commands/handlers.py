"""
指令處理器

根據 ParsedCommand 產生回覆文字，並呼叫服務層完成 CRUD。
"""

import logging
from collections.abc import Callable

from linebot.v3.messaging import MessageAction, QuickReply, QuickReplyItem

from commands import alert_service, price_fetcher, watch_service
from commands.models import CommandType, ParsedCommand
from commands.parser import is_stock_code

logger = logging.getLogger(__name__)

# 說明訊息（集中管理，方便後續調整）
HELP_MESSAGE = """📊 Watch It 台股盯盤 Bot

【自選股】
• 加自選 2330   加入自選股
• 自選          查看自選股清單
• 刪自選 2330   移除自選股

【觸價警示】（須先加入自選股）
• 警示 2330 < 1000   設定「低於 1000」時通知
• 警示 2330 > 1200   設定「高於 1200」時通知
• 警示清單           查看我的警示
• 改警示 3 < 1050    修改第 3 號警示
• 刪警示 3           刪除第 3 號警示
• 清空警示           清空全部（需二次確認）

【查詢股價】（開發中）
• 2330          直接輸入代號
• 查詢 2330     查詢指定代號

【其他】
• 幫助          顯示此說明"""


def handle_help(_: ParsedCommand, __: str) -> tuple[str, QuickReply | None]:
    """回傳指令說明。"""
    quick_reply = QuickReply(
        items=[
            QuickReplyItem(action=MessageAction(label="查自選股", text="自選")),
            QuickReplyItem(action=MessageAction(label="查警示清單", text="警示清單")),
            QuickReplyItem(action=MessageAction(label="使用說明", text="幫助")),
        ]
    )
    return HELP_MESSAGE, quick_reply


def handle_query(command: ParsedCommand, _: str) -> tuple[str, QuickReply | None]:
    """
    處理查詢指令。
    """
    target = command.target or ""

    if not is_stock_code(target):
        logger.info("查詢指令：非股票代號格式 %s", target)
        return "目前僅支援以股票代號查詢，例如「查詢 2330」", None

    logger.info("查詢指令：代號 %s", target)
    
    result = price_fetcher.get_stock_price(target)
    if result is None:
        return f"查不到代號 {target} 的股價，請確認代號是否正確", None

    code = result.get("code", target)
    name = result.get("name", "")
    price = result.get("price", "無資料")
    time_str = result.get("time", "無資料")
    
    reply = (
        f"📈 {code} {name}".strip() + "\n"
        f"當前價格：{price}\n"
        f"資料時間：{time_str}"
    )

    if not result.get("is_realtime", True):
        reply += "\n⚠️ 此為非即時報價（盤後或休市），僅供參考"

    return reply, None


def handle_add_watch(command: ParsedCommand, line_user_id: str) -> tuple[str, QuickReply | None]:
    """處理加入自選股指令。"""
    target = command.target or ""
    logger.info("加自選指令：%s", target)
    reply_text = watch_service.add_watch(line_user_id, target)
    
    quick_reply = None
    # 待重構：目前使用文字來判斷成功與否較為脆弱（萬一文案改了就失效）。
    # 未來若 watch_service 改為回傳明確狀態（如 bool），優先用狀態來判斷。
    if "✅" in reply_text and target:
        quick_reply = QuickReply(
            items=[
                QuickReplyItem(action=MessageAction(label="設定此股警示", text=f"警示 {target} ")),
                QuickReplyItem(action=MessageAction(label="查自選股", text="自選")),
            ]
        )
    return reply_text, quick_reply


def handle_remove_watch(command: ParsedCommand, line_user_id: str) -> tuple[str, QuickReply | None]:
    """處理移除自選股指令。"""
    target = command.target or ""
    logger.info("刪自選指令：%s", target)
    return watch_service.remove_watch(line_user_id, target), None


def handle_list_watch(_: ParsedCommand, line_user_id: str) -> tuple[str, QuickReply | None]:
    """處理自選股清單指令。"""
    logger.info("自選清單指令")
    reply_text = watch_service.list_watches(line_user_id)
    quick_reply = QuickReply(
        items=[
            QuickReplyItem(action=MessageAction(label="查警示清單", text="警示清單")),
            QuickReplyItem(action=MessageAction(label="新增警示提示", text="幫助")),
        ]
    )
    return reply_text, quick_reply


def handle_add_alert(command: ParsedCommand, line_user_id: str) -> tuple[str, QuickReply | None]:
    """處理新增警示指令。"""
    if (
        command.target is None
        or command.operator is None
        or command.target_price is None
    ):
        return "❌ 指令格式錯誤。", None

    logger.info(
        "新增警示：%s %s %s",
        command.target,
        command.operator,
        command.target_price,
    )
    return alert_service.add_alert(
        line_user_id,
        command.target,
        command.operator,
        command.target_price,
    ), None


def handle_list_alert(_: ParsedCommand, line_user_id: str) -> tuple[str, QuickReply | None]:
    """處理警示清單指令。"""
    logger.info("警示清單指令")
    reply_text = alert_service.list_alerts(line_user_id)
    quick_reply = QuickReply(
        items=[
            QuickReplyItem(action=MessageAction(label="查自選股", text="自選")),
            QuickReplyItem(action=MessageAction(label="清空警示", text="清空警示")),
        ]
    )
    return reply_text, quick_reply


def handle_update_alert(command: ParsedCommand, line_user_id: str) -> tuple[str, QuickReply | None]:
    """處理修改警示指令。"""
    if (
        command.alert_index is None
        or command.operator is None
        or command.target_price is None
    ):
        return "❌ 指令格式錯誤。", None

    logger.info(
        "修改警示 #%s：%s %s",
        command.alert_index,
        command.operator,
        command.target_price,
    )
    return alert_service.update_alert(
        line_user_id,
        command.alert_index,
        command.operator,
        command.target_price,
    ), None


def handle_delete_alert(command: ParsedCommand, line_user_id: str) -> tuple[str, QuickReply | None]:
    """處理刪除警示指令。"""
    if command.alert_index is None:
        return "❌ 指令格式錯誤。", None

    logger.info("刪除警示 #%s", command.alert_index)
    return alert_service.delete_alert(line_user_id, command.alert_index), None


def handle_clear_alerts(_: ParsedCommand, line_user_id: str) -> tuple[str, QuickReply | None]:
    """
    處理清空警示第一段。

    若目前沒有警示，直接回覆，不進入確認流程。
    """
    logger.info("清空警示（第一段）")
    if alert_service.count_alerts(line_user_id) == 0:
        return "你目前沒有警示", None

    return (
        "⚠️ 此操作將刪除你所有的警示。\n"
        "確認清空請輸入：清空警示 confirm"
    ), None


def handle_confirm_clear_alerts(_: ParsedCommand, line_user_id: str) -> tuple[str, QuickReply | None]:
    """處理清空警示第二段（確認執行）。"""
    logger.info("清空警示（確認執行）")
    return alert_service.clear_alerts(line_user_id), None


def handle_unknown(command: ParsedCommand, _: str) -> tuple[str, QuickReply | None]:
    """處理無法辨識的指令。"""
    display_text = command.raw_text.strip() or "（空白）"
    logger.info("無法辨識指令：%s", display_text)
    quick_reply = QuickReply(
        items=[
            QuickReplyItem(action=MessageAction(label="查自選股", text="自選")),
            QuickReplyItem(action=MessageAction(label="查警示清單", text="警示清單")),
            QuickReplyItem(action=MessageAction(label="使用說明", text="幫助")),
        ]
    )
    return HELP_MESSAGE, quick_reply


# 指令類型 → 處理函式 對照表
HANDLERS: dict[CommandType, Callable[[ParsedCommand, str], tuple[str, QuickReply | None]]] = {
    CommandType.HELP: handle_help,
    CommandType.QUERY: handle_query,
    CommandType.ADD_WATCH: handle_add_watch,
    CommandType.REMOVE_WATCH: handle_remove_watch,
    CommandType.LIST_WATCH: handle_list_watch,
    CommandType.ADD_ALERT: handle_add_alert,
    CommandType.LIST_ALERT: handle_list_alert,
    CommandType.UPDATE_ALERT: handle_update_alert,
    CommandType.DELETE_ALERT: handle_delete_alert,
    CommandType.CLEAR_ALERTS: handle_clear_alerts,
    CommandType.CONFIRM_CLEAR_ALERTS: handle_confirm_clear_alerts,
    CommandType.UNKNOWN: handle_unknown,
}


def dispatch_command(command: ParsedCommand, line_user_id: str) -> tuple[str, QuickReply | None]:
    """
    分派指令至對應處理器並回傳回覆文字與選單（QuickReply）。

    Args:
        command: 已解析的指令物件。
        line_user_id: LINE 使用者 ID。

    Returns:
        (回傳給使用者的文字訊息, QuickReply 物件或 None)
    """
    # 解析階段已發現格式錯誤，直接回覆
    if command.parse_error:
        quick_reply = QuickReply(
            items=[
                QuickReplyItem(action=MessageAction(label="查自選股", text="自選")),
                QuickReplyItem(action=MessageAction(label="查警示清單", text="警示清單")),
                QuickReplyItem(action=MessageAction(label="使用說明", text="幫助")),
            ]
        )
        return command.parse_error, quick_reply

    handler = HANDLERS.get(command.type, handle_unknown)
    return handler(command, line_user_id)
