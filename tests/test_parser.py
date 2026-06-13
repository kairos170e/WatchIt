"""
指令解析器測試
"""

from decimal import Decimal

import pytest

from commands.models import CommandType
from commands.parser import parse_command, validate_price


class TestValidatePrice:
    """價格驗證測試。"""

    @pytest.mark.parametrize(
        "price_str, expected",
        [
            ("1000", Decimal("1000.00")),
            ("99.5", Decimal("99.50")),
            ("0.01", Decimal("0.01")),
        ],
    )
    def test_valid_prices(self, price_str, expected):
        assert validate_price(price_str) == expected

    @pytest.mark.parametrize(
        "price_str",
        ["-1", "0", "abc", "100.999", ""],
    )
    def test_invalid_prices(self, price_str):
        assert validate_price(price_str) is None


class TestParseCommand:
    """指令解析測試。"""

    def test_help_command(self):
        cmd = parse_command("幫助")
        assert cmd.type == CommandType.HELP

    def test_add_watch(self):
        cmd = parse_command("加自選 2330")
        assert cmd.type == CommandType.ADD_WATCH
        assert cmd.target == "2330"

    def test_list_watch(self):
        cmd = parse_command("自選")
        assert cmd.type == CommandType.LIST_WATCH

    def test_direct_stock_code_query(self):
        cmd = parse_command("2330")
        assert cmd.type == CommandType.QUERY
        assert cmd.target == "2330"

    def test_fullwidth_digits_normalized(self):
        cmd = parse_command("加自選 ２３３０")
        assert cmd.type == CommandType.ADD_WATCH
        assert cmd.target == "2330"

    def test_add_alert_valid(self):
        cmd = parse_command("警示 2330 < 1000")
        assert cmd.type == CommandType.ADD_ALERT
        assert cmd.target == "2330"
        assert cmd.operator == "<"
        assert cmd.target_price == Decimal("1000.00")
        assert cmd.parse_error is None

    def test_add_alert_invalid_price(self):
        cmd = parse_command("警示 2330 < -100")
        assert cmd.parse_error is not None

    def test_add_alert_three_decimal_places(self):
        cmd = parse_command("警示 2330 < 1000.123")
        assert cmd.parse_error is not None

    def test_list_alert(self):
        cmd = parse_command("警示清單")
        assert cmd.type == CommandType.LIST_ALERT

    def test_update_alert(self):
        cmd = parse_command("改警示 3 < 1050")
        assert cmd.type == CommandType.UPDATE_ALERT
        assert cmd.alert_index == 3
        assert cmd.operator == "<"
        assert cmd.target_price == Decimal("1050.00")

    def test_delete_alert(self):
        cmd = parse_command("刪警示 2")
        assert cmd.type == CommandType.DELETE_ALERT
        assert cmd.alert_index == 2

    def test_delete_alert_zero_index(self):
        cmd = parse_command("刪警示 0")
        assert cmd.parse_error is not None

    def test_clear_alerts(self):
        cmd = parse_command("清空警示")
        assert cmd.type == CommandType.CLEAR_ALERTS

    def test_confirm_clear_alerts(self):
        cmd = parse_command("清空警示 confirm")
        assert cmd.type == CommandType.CONFIRM_CLEAR_ALERTS

        cmd_upper = parse_command("清空警示 CONFIRM")
        assert cmd_upper.type == CommandType.CONFIRM_CLEAR_ALERTS

    def test_unknown_command(self):
        cmd = parse_command("随便乱打")
        assert cmd.type == CommandType.UNKNOWN

    def test_empty_message(self):
        cmd = parse_command("   ")
        assert cmd.type == CommandType.UNKNOWN
