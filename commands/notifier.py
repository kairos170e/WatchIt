"""
主動推播服務
"""

import logging
from decimal import Decimal

from linebot.v3.messaging import (
    MessagingApi,
    PushMessageRequest,
    TextMessage,
)

logger = logging.getLogger(__name__)

def push_alert_notification(
    messaging_api: MessagingApi,
    line_user_id: str,
    stock_code: str,
    stock_name: str,
    operator: str,
    target_price: Decimal,
    current_price: Decimal,
    time_str: str,
    is_realtime: bool = True,
) -> bool:
    """
    推播觸價警示通知給使用者。
    
    Args:
        messaging_api: LINE Messaging API 實例。
        line_user_id: 接收通知的使用者 ID。
        stock_code: 股票代號。
        stock_name: 股票名稱。
        operator: 條件運算子 (">" 或 "<")。
        target_price: 目標價格。
        current_price: 當前價格。
        time_str: 價格時間字串。
        is_realtime: 是否為即時報價，若為 False 則會加上非即時警語。
        
    Returns:
        bool: 推播是否成功。
    """
    op_str = "大於等於" if operator == ">" else "小於等於"
    
    text = (
        f"🚨 觸價警示通知 🚨\n\n"
        f"【{stock_code} {stock_name}】\n"
        f"當前價格：{current_price}\n"
        f"目標條件：{op_str} {target_price}\n"
        f"資料時間：{time_str}"
    )

    if not is_realtime:
        text += "\n\n⚠️ 此為非即時報價（盤後或休市），僅供參考"
    
    try:
        push_req = PushMessageRequest(
            to=line_user_id,
            messages=[TextMessage(text=text)]
        )
        messaging_api.push_message(push_req)
        logger.info(f"成功推播警示給 {line_user_id}: {stock_code} {op_str} {target_price}")
        return True
    except Exception as e:
        logger.exception(f"推播警示失敗給 {line_user_id} ({stock_code}): {e}")
        return False
