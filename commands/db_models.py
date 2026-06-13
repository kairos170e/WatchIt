"""
資料庫 ORM 模型

與 commands/models.py 的指令解析 dataclass 分離，避免混淆。
使用 SQLAlchemy 2.0 新式寫法：DeclarativeBase + Mapped + mapped_column。
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """所有 ORM 模型的基礎類別。"""


class WatchItem(Base):
    """
    自選股資料表。

    同一使用者不可重複加入相同代號（UniqueConstraint）。
    僅有加入/刪除操作，屬不可變資料，故不設 updated_at。
    """

    __tablename__ = "watch_items"
    __table_args__ = (
        UniqueConstraint(
            "line_user_id",
            "stock_code",
            name="uq_watch_user_stock",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    line_user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    stock_code: Mapped[str] = mapped_column(String(6), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )


class Alert(Base):
    """
    觸價警示資料表。

    operator 僅允許 ">"（高於）或 "<"（低於）。
    target_price 使用 Numeric，禁止 float，避免浮點精度問題。
    """

    __tablename__ = "alerts"
    __table_args__ = (
        UniqueConstraint(
            "line_user_id",
            "stock_code",
            "operator",
            "target_price",
            name="uq_alert_user_stock_op_price",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    line_user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    stock_code: Mapped[str] = mapped_column(String(6), nullable=False)
    operator: Mapped[str] = mapped_column(String(1), nullable=False)
    target_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    is_triggered: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="0",
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
