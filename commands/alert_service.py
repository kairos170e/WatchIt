"""
觸價警示服務層

提供警示的 add / list / update / delete / clear 操作。
每位使用者上限 10 筆；新增時強制股票須已在自選股清單。
使用者看到的序號為 1、2、3…，不暴露資料庫 id。
"""

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from commands.database import get_session
from commands.db_models import Alert, WatchItem
from commands.parser import is_stock_code

# 每位使用者警示上限
MAX_ALERTS = 10


def _format_price(price: Decimal) -> str:
    """將 Decimal 價格格式化為最多兩位小數的字串。"""
    return f"{price.quantize(Decimal('0.01')):,.2f}"


def _operator_label(operator: str) -> str:
    """將運算子轉為中文描述。"""
    if operator == ">":
        return "高於"
    if operator == "<":
        return "低於"
    return operator


def _get_user_alerts(session: Session, line_user_id: str) -> list[Alert]:
    """取得使用者所有警示，依建立時間排序。"""
    return list(
        session.scalars(
            select(Alert)
            .where(Alert.line_user_id == line_user_id)
            .order_by(Alert.created_at.asc())
        ).all()
    )


def count_alerts(line_user_id: str) -> int:
    """
    計算使用者目前的警示數量。

    Args:
        line_user_id: LINE 使用者 ID。

    Returns:
        警示筆數。
    """
    with get_session() as session:
        count = session.scalar(
            select(func.count())
            .select_from(Alert)
            .where(Alert.line_user_id == line_user_id)
        )
        return count or 0


def add_alert(
    line_user_id: str,
    stock_code: str,
    operator: str,
    target_price: Decimal,
) -> str:
    """
    新增觸價警示。

    股票必須已在自選股清單；否則回覆含下一步操作的提示。

    Args:
        line_user_id: LINE 使用者 ID。
        stock_code: 股票代號。
        operator: ">" 或 "<"。
        target_price: 觸發價格（Decimal）。

    Returns:
        操作結果訊息。
    """
    if not is_stock_code(stock_code):
        return "❌ 股票代號格式不正確。請輸入 4～6 位數字代號。"

    if operator not in (">", "<"):
        return "❌ 運算子僅支援 >（高於）或 <（低於）。"

    with get_session() as session:
        # 強制檢查自選股
        watch_item = session.scalar(
            select(WatchItem).where(
                WatchItem.line_user_id == line_user_id,
                WatchItem.stock_code == stock_code,
            )
        )
        if watch_item is None:
            return (
                f"❌ {stock_code} 不在你的自選清單。"
                f"請先輸入「加自選 {stock_code}」再設定警示。"
            )

        count = session.scalar(
            select(func.count())
            .select_from(Alert)
            .where(Alert.line_user_id == line_user_id)
        )
        if count is not None and count >= MAX_ALERTS:
            return f"❌ 警示已達上限（{MAX_ALERTS} 筆），請先刪除部分警示。"

        try:
            session.add(
                Alert(
                    line_user_id=line_user_id,
                    stock_code=stock_code,
                    operator=operator,
                    target_price=target_price,
                )
            )
            session.flush()
        except IntegrityError:
            session.rollback()
            op_label = _operator_label(operator)
            return (
                f"❌ 已存在相同警示：{stock_code} {op_label} "
                f"{_format_price(target_price)}"
            )

    op_label = _operator_label(operator)
    return (
        f"✅ 已設定警示：{stock_code} {op_label} "
        f"{_format_price(target_price)}"
    )


def list_alerts(line_user_id: str) -> str:
    """
    列出使用者所有警示（含使用者序號）。

    Args:
        line_user_id: LINE 使用者 ID。

    Returns:
        格式化的清單文字。
    """
    with get_session() as session:
        rows = session.execute(
            select(Alert.stock_code, Alert.operator, Alert.target_price)
            .where(Alert.line_user_id == line_user_id)
            .order_by(Alert.created_at.asc())
        ).all()

    if not rows:
        return "📋 你目前沒有警示。\n輸入「警示 2330 < 1000」開始設定。"

    lines = [f"📋 你的警示清單（共 {len(rows)} 筆）", ""]
    for index, (stock_code, operator, target_price) in enumerate(rows, start=1):
        op_label = _operator_label(operator)
        lines.append(
            f"{index}. {stock_code} {op_label} {_format_price(target_price)}"
        )

    return "\n".join(lines)


def update_alert(
    line_user_id: str,
    alert_index: int,
    operator: str,
    target_price: Decimal,
) -> str:
    """
    修改指定序號的警示。

    Args:
        line_user_id: LINE 使用者 ID。
        alert_index: 使用者序號（1 起算）。
        operator: ">" 或 "<"。
        target_price: 新的觸發價格。

    Returns:
        操作結果訊息。
    """
    if operator not in (">", "<"):
        return "❌ 運算子僅支援 >（高於）或 <（低於）。"

    with get_session() as session:
        alerts = _get_user_alerts(session, line_user_id)

        if alert_index < 1 or alert_index > len(alerts):
            return f"❌ 找不到第 {alert_index} 號警示。請輸入「警示清單」查看。"

        alert = alerts[alert_index - 1]
        stock_code = alert.stock_code

        alert.operator = operator
        alert.target_price = target_price

        try:
            session.flush()
        except IntegrityError:
            session.rollback()
            op_label = _operator_label(operator)
            return (
                f"❌ 已存在相同警示：{stock_code} {op_label} "
                f"{_format_price(target_price)}"
            )

    op_label = _operator_label(operator)
    return (
        f"✅ 已更新第 {alert_index} 號警示：{stock_code} {op_label} "
        f"{_format_price(target_price)}"
    )


def delete_alert(line_user_id: str, alert_index: int) -> str:
    """
    刪除指定序號的警示。

    Args:
        line_user_id: LINE 使用者 ID。
        alert_index: 使用者序號（1 起算）。

    Returns:
        操作結果訊息。
    """
    with get_session() as session:
        alerts = _get_user_alerts(session, line_user_id)

        if alert_index < 1 or alert_index > len(alerts):
            return f"❌ 找不到第 {alert_index} 號警示。請輸入「警示清單」查看。"

        alert = alerts[alert_index - 1]
        stock_code = alert.stock_code
        op_label = _operator_label(alert.operator)
        price_text = _format_price(alert.target_price)

        session.delete(alert)

    return f"✅ 已刪除第 {alert_index} 號警示：{stock_code} {op_label} {price_text}"


def clear_alerts(line_user_id: str) -> str:
    """
    清空使用者所有警示。

    Args:
        line_user_id: LINE 使用者 ID。

    Returns:
        操作結果訊息。
    """
    with get_session() as session:
        alerts = _get_user_alerts(session, line_user_id)
        count = len(alerts)

        if count == 0:
            return "你目前沒有警示"

        for alert in alerts:
            session.delete(alert)

    return f"✅ 已清空所有警示（共 {count} 筆）"
