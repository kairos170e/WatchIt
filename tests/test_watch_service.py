"""
自選股服務層測試
"""

from commands import watch_service

USER_ID = "U_test_watch_user"


class TestWatchService:
    """自選股 CRUD 測試。"""

    def test_add_and_list(self):
        result = watch_service.add_watch(USER_ID, "2330")
        assert "✅" in result

        listing = watch_service.list_watches(USER_ID)
        assert "2330" in listing
        assert "1." in listing

    def test_duplicate_add(self):
        watch_service.add_watch(USER_ID, "2330")
        result = watch_service.add_watch(USER_ID, "2330")
        assert "已在" in result

    def test_remove_watch(self):
        watch_service.add_watch(USER_ID, "2330")
        result = watch_service.remove_watch(USER_ID, "2330")
        assert "✅" in result

        listing = watch_service.list_watches(USER_ID)
        assert "空的" in listing

    def test_remove_nonexistent(self):
        result = watch_service.remove_watch(USER_ID, "2330")
        assert "不在" in result

    def test_invalid_stock_code(self):
        result = watch_service.add_watch(USER_ID, "abc")
        assert "格式不正確" in result

    def test_max_watch_items(self):
        for i in range(20):
            code = f"{1000 + i}"
            watch_service.add_watch(USER_ID, code)

        result = watch_service.add_watch(USER_ID, "9999")
        assert "上限" in result

    def test_user_serial_numbers(self):
        watch_service.add_watch(USER_ID, "2330")
        watch_service.add_watch(USER_ID, "0050")

        listing = watch_service.list_watches(USER_ID)
        assert "1. 2330" in listing
        assert "2. 0050" in listing
