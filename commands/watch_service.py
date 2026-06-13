"""
自選股服務層

提供自選股的 add / list / remove 操作。
每位使用者上限 20 檔；重複新增捕捉 IntegrityError 回覆友善訊息。
"""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from commands.database import get_session
from commands.db_models import Alert, WatchItem
from commands.parser import is_stock_code

# 每位使用者自選股上限
MAX_WATCH_ITEMS = 20


def add_watch(line_user_id: str, stock_code: str) -> str:
    """
    加入自選股。

    Args:
        line_user_id: LINE 使用者 ID。
        stock_code: 股票代號。

    Returns:
        操作結果訊息。
    """
    if not is_stock_code(stock_code):
        return "❌ 股票代號格式不正確。請輸入 4～6 位數字代號。"

    with get_session() as session:
        count = session.scalar(
            select(func.count())
            .select_from(WatchItem)
            .where(WatchItem.line_user_id == line_user_id)
        )
        if count is not None and count >= MAX_WATCH_ITEMS:
            return f"❌ 自選股已達上限（{MAX_WATCH_ITEMS} 檔），請先刪除部分自選股。"

        try:
            session.add(
                WatchItem(line_user_id=line_user_id, stock_code=stock_code)
            )
            session.flush()
        except IntegrityError:
            session.rollback()
            return f"❌ {stock_code} 已在你的自選股清單中。"

    return f"✅ 已加入自選股：{stock_code}"


def list_watches(line_user_id: str) -> str:
    """
    列出使用者的自選股清單（使用者序號 1 起算）。

    Args:
        line_user_id: LINE 使用者 ID。

    Returns:
        格式化的清單文字。
    """
    with get_session() as session:
        stock_codes = list(
            session.scalars(
                select(WatchItem.stock_code)
                .where(WatchItem.line_user_id == line_user_id)
                .order_by(WatchItem.created_at.asc())
            ).all()
        )

    if not stock_codes:
        return "📋 你的自選股清單目前是空的。\n輸入「加自選 2330」開始建立。"

    lines = [f"📋 你的自選股清單（共 {len(stock_codes)} 檔）", ""]
    for index, code in enumerate(stock_codes, start=1):
        lines.append(f"{index}. {code}")

    return "\n".join(lines)


def remove_watch(line_user_id: str, stock_code: str) -> str:
    """
    移除自選股。

    若該代號有關聯警示，一併刪除以保持資料一致。

    Args:
        line_user_id: LINE 使用者 ID。
        stock_code: 股票代號。

    Returns:
        操作結果訊息。
    """
    if not is_stock_code(stock_code):
        return "❌ 股票代號格式不正確。請輸入 4～6 位數字代號。"

    with get_session() as session:
        item = session.scalar(
            select(WatchItem).where(
                WatchItem.line_user_id == line_user_id,
                WatchItem.stock_code == stock_code,
            )
        )
        if item is None:
            return f"❌ {stock_code} 不在你的自選股清單中。"

        # 刪除該代號的所有警示（自選股移除後不應保留孤立警示）
        related_alerts = session.scalars(
            select(Alert).where(
                Alert.line_user_id == line_user_id,
                Alert.stock_code == stock_code,
            )
        ).all()
        removed_alerts = len(related_alerts)
        for alert in related_alerts:
            session.delete(alert)
        session.delete(item)

    if removed_alerts > 0:
        return (
            f"✅ 已移除自選股：{stock_code}\n"
            f"（同時刪除 {removed_alerts} 筆相關警示）"
        )
    return f"✅ 已移除自選股：{stock_code}"
