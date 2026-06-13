"""
觸價警示服務層測試
"""

from decimal import Decimal

from commands import alert_service, watch_service

USER_ID = "U_test_alert_user"


class TestAlertService:
    """警示 CRUD 測試。"""

    def _setup_watch(self, stock_code: str = "2330") -> None:
        watch_service.add_watch(USER_ID, stock_code)

    def test_add_alert_requires_watchlist(self):
        result = alert_service.add_alert(USER_ID, "2330", "<", Decimal("1000"))
        assert "不在你的自選清單" in result
        assert "加自選 2330" in result

    def test_add_and_list(self):
        self._setup_watch()
        result = alert_service.add_alert(USER_ID, "2330", "<", Decimal("1000"))
        assert "✅" in result

        listing = alert_service.list_alerts(USER_ID)
        assert "1." in listing
        assert "2330" in listing
        assert "低於" in listing

    def test_duplicate_alert(self):
        self._setup_watch()
        alert_service.add_alert(USER_ID, "2330", "<", Decimal("1000"))
        result = alert_service.add_alert(USER_ID, "2330", "<", Decimal("1000"))
        assert "已存在" in result

    def test_update_alert(self):
        self._setup_watch()
        alert_service.add_alert(USER_ID, "2330", "<", Decimal("1000"))
        result = alert_service.update_alert(
            USER_ID, 1, "<", Decimal("1050.00")
        )
        assert "✅" in result

        listing = alert_service.list_alerts(USER_ID)
        assert "1,050.00" in listing

    def test_update_out_of_range(self):
        self._setup_watch()
        alert_service.add_alert(USER_ID, "2330", "<", Decimal("1000"))
        result = alert_service.update_alert(
            USER_ID, 99, "<", Decimal("1050")
        )
        assert "找不到" in result

    def test_delete_alert(self):
        self._setup_watch()
        alert_service.add_alert(USER_ID, "2330", "<", Decimal("1000"))
        result = alert_service.delete_alert(USER_ID, 1)
        assert "✅" in result
        assert alert_service.count_alerts(USER_ID) == 0

    def test_delete_out_of_range(self):
        result = alert_service.delete_alert(USER_ID, 1)
        assert "找不到" in result

    def test_max_alerts(self):
        self._setup_watch()
        for i in range(10):
            price = Decimal(f"{1000 + i}.00")
            alert_service.add_alert(USER_ID, "2330", "<", price)

        result = alert_service.add_alert(
            USER_ID, "2330", "<", Decimal("2000.00")
        )
        assert "上限" in result

    def test_clear_alerts(self):
        self._setup_watch()
        alert_service.add_alert(USER_ID, "2330", "<", Decimal("1000"))
        result = alert_service.clear_alerts(USER_ID)
        assert "清空" in result
        assert alert_service.count_alerts(USER_ID) == 0

    def test_clear_alerts_when_empty(self):
        result = alert_service.clear_alerts(USER_ID)
        assert result == "你目前沒有警示"

    def test_decimal_precision(self):
        self._setup_watch()
        alert_service.add_alert(USER_ID, "2330", "<", Decimal("999.99"))
        listing = alert_service.list_alerts(USER_ID)
        assert "999.99" in listing

    def test_user_serial_numbers(self):
        self._setup_watch("2330")
        watch_service.add_watch(USER_ID, "0050")
        alert_service.add_alert(USER_ID, "2330", "<", Decimal("1000"))
        alert_service.add_alert(USER_ID, "0050", ">", Decimal("150"))

        listing = alert_service.list_alerts(USER_ID)
        assert "1. 2330" in listing
        assert "2. 0050" in listing
