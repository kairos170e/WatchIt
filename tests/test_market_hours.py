"""
測試市場交易時間判斷模組
"""

from datetime import datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from commands.market_hours import is_market_open


class TestMarketHours:
    def test_market_open_weekday_during_hours(self):
        """測試平日盤中"""
        # 2026-06-15 星期一 10:00:00
        tz = ZoneInfo("Asia/Taipei")
        dt = datetime(2026, 6, 15, 10, 0, 0, tzinfo=tz)
        assert is_market_open(dt) is True

        # 剛好開盤 09:00:00
        dt_open = datetime(2026, 6, 15, 9, 0, 0, tzinfo=tz)
        assert is_market_open(dt_open) is True

        # 13:29:59 應為盤中
        dt_before_close = datetime(2026, 6, 15, 13, 29, 59, tzinfo=tz)
        assert is_market_open(dt_before_close) is True

    def test_market_closed_weekday_before_hours(self):
        """測試平日盤前"""
        # 2026-06-15 星期一 08:59:59
        tz = ZoneInfo("Asia/Taipei")
        dt = datetime(2026, 6, 15, 8, 59, 59, tzinfo=tz)
        assert is_market_open(dt) is False

    def test_market_closed_weekday_after_hours(self):
        """測試平日盤後"""
        tz = ZoneInfo("Asia/Taipei")
        # 剛好收盤 13:30:00 (應為非盤中)
        dt_close = datetime(2026, 6, 15, 13, 30, 0, tzinfo=tz)
        assert is_market_open(dt_close) is False

        # 2026-06-15 星期一 13:30:01
        dt_after = datetime(2026, 6, 15, 13, 30, 1, tzinfo=tz)
        assert is_market_open(dt_after) is False

    def test_market_closed_weekend(self):
        """測試週末"""
        tz = ZoneInfo("Asia/Taipei")
        # 2026-06-13 星期六 10:00:00
        dt_sat = datetime(2026, 6, 13, 10, 0, 0, tzinfo=tz)
        assert is_market_open(dt_sat) is False

        # 2026-06-14 星期日 10:00:00
        dt_sun = datetime(2026, 6, 14, 10, 0, 0, tzinfo=tz)
        assert is_market_open(dt_sun) is False
