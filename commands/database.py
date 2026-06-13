"""
資料庫連線與 Session 管理

正式環境使用專案根目錄的 watchit.db。
測試時可透過 configure() 注入 in-memory SQLite URL。
"""

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from commands.db_models import Base

# 正式環境 SQLite 檔案路徑
DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "watchit.db"
DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_DB_PATH.as_posix()}"

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def configure(database_url: str | None = None) -> None:
    """
    設定資料庫連線。

    Args:
        database_url: 資料庫 URL；未指定時使用 watchit.db。
    """
    global _engine, _session_factory

    url = database_url or DEFAULT_DATABASE_URL
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}

    _engine = create_engine(url, connect_args=connect_args, echo=False)
    _session_factory = sessionmaker(bind=_engine, autoflush=False, autocommit=False)


@contextmanager
def get_session() -> Iterator[Session]:
    """
    提供資料庫 Session 的 context manager。

    成功時自動 commit，發生例外時 rollback，結束時關閉 session。
    """
    if _session_factory is None:
        configure()

    session = _session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """建立所有資料表（若尚不存在）。"""
    if _engine is None:
        configure()
    Base.metadata.create_all(_engine)


def reset_engine() -> None:
    """重設 engine 與 session factory（供測試使用）。"""
    global _engine, _session_factory

    if _engine is not None:
        _engine.dispose()

    _engine = None
    _session_factory = None
