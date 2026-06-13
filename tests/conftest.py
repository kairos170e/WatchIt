"""
pytest 共用 fixture

每個測試使用 in-memory SQLite，不碰正式 watchit.db。
"""

import pytest

from commands.database import configure, init_db, reset_engine


@pytest.fixture(autouse=True)
def setup_in_memory_db():
    """每個測試前後重置並初始化 in-memory 資料庫。"""
    reset_engine()
    configure("sqlite:///:memory:")
    init_db()
    yield
    reset_engine()
