"""
指令資料模型

定義 Bot 可辨識的指令類型，以及解析後的結構化結果。
（與 db_models.py 的 ORM 模型不同，請勿混淆。）
"""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum


class CommandType(str, Enum):
    """使用者指令類型。"""

    HELP = "help"  # 顯示說明
    QUERY = "query"  # 查詢股價（第三階段）
    ADD_WATCH = "add_watch"  # 加入自選股
    REMOVE_WATCH = "remove_watch"  # 移除自選股
    LIST_WATCH = "list_watch"  # 查看自選股清單
    ADD_ALERT = "add_alert"  # 新增觸價警示
    LIST_ALERT = "list_alert"  # 查看警示清單
    UPDATE_ALERT = "update_alert"  # 修改指定序號的警示
    DELETE_ALERT = "delete_alert"  # 刪除指定序號的警示
    CLEAR_ALERTS = "clear_alerts"  # 清空警示（第一段：提示確認）
    CONFIRM_CLEAR_ALERTS = "confirm_clear_alerts"  # 清空警示（第二段：確認執行，輸入「清空警示 confirm」）
    UNKNOWN = "unknown"  # 無法辨識


@dataclass
class ParsedCommand:
    """
    解析後的指令物件。

    Attributes:
        type: 指令類型。
        raw_text: 使用者原始輸入（未正規化）。
        target: 查詢/操作的標的（股票代號或名稱關鍵字）。
        args: 額外參數（保留供後續擴充）。
        alert_index: 警示清單中的使用者序號（1 起算）。
        operator: 價格比較運算子（">" 或 "<"）。
        target_price: 觸發價格（Decimal，禁止 float）。
        parse_error: 解析階段發現格式錯誤時的友善提示訊息。
    """

    type: CommandType
    raw_text: str
    target: str | None = None
    args: list[str] = field(default_factory=list)
    alert_index: int | None = None
    operator: str | None = None
    target_price: Decimal | None = None
    parse_error: str | None = None
