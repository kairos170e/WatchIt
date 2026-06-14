"""
股價抓取服務測試
"""

import concurrent.futures
from decimal import Decimal
from unittest.mock import MagicMock, patch

from commands.price_fetcher import get_stock_price


class TestPriceFetcher:
    """測試 price_fetcher.py"""

    @patch("commands.price_fetcher.twstock")
    def test_get_stock_price_success_realtime(self, mock_twstock):
        """測試正常抓取即時資料"""
        mock_twstock.realtime.get.return_value = {
            "success": True,
            "info": {
                "code": "2330",
                "name": "台積電",
                "time": "2026-06-12 14:30:00"
            },
            "realtime": {
                "latest_trade_price": "1050.50"
            }
        }

        result = get_stock_price("2330")

        assert result is not None
        assert result["code"] == "2330"
        assert result["name"] == "台積電"
        assert result["price"] == Decimal("1050.50")
        assert result["time"] == "2026-06-12 14:30:00"
        assert result["is_realtime"] is True
        mock_twstock.realtime.get.assert_called_once_with("2330")
        mock_twstock.Stock.assert_not_called()

    @patch("commands.price_fetcher.twstock")
    def test_get_stock_price_invalid_stock(self, mock_twstock):
        """測試查無股票（success=False）"""
        mock_twstock.realtime.get.return_value = {
            "success": False,
            "rtmessage": "Invalid Stock ID."
        }

        result = get_stock_price("9999")
        assert result is None

    @patch("commands.price_fetcher.twstock")
    def test_get_stock_price_fallback_to_close(self, mock_twstock):
        """測試盤後無即時資料時降級抓取歷史收盤價"""
        mock_twstock.realtime.get.return_value = {
            "success": True,
            "info": {
                "code": "2330",
                "name": "台積電",
                "time": "2026-06-12 08:30:00"
            },
            "realtime": {
                "latest_trade_price": "-"  # 盤前或盤後無即時資料
            }
        }
        
        # Mock twstock.Stock
        mock_stock_instance = MagicMock()
        mock_stock_instance.price = [1000.0, 1010.0, 1020.50]
        mock_twstock.Stock.return_value = mock_stock_instance

        result = get_stock_price("2330")

        assert result is not None
        assert result["code"] == "2330"
        assert result["name"] == "台積電"
        assert result["price"] == Decimal("1020.50")
        assert result["is_realtime"] is False
        mock_twstock.Stock.assert_called_once_with("2330")

    @patch("commands.price_fetcher.twstock")
    def test_get_stock_price_fallback_fails(self, mock_twstock):
        """測試降級抓取時也沒有歷史資料"""
        mock_twstock.realtime.get.return_value = {
            "success": True,
            "info": {"code": "2330"},
            "realtime": {"latest_trade_price": "-"}
        }
        mock_stock_instance = MagicMock()
        mock_stock_instance.price = []  # 空的歷史紀錄
        mock_twstock.Stock.return_value = mock_stock_instance

        result = get_stock_price("2330")
        assert result is None

    @patch("commands.price_fetcher._fetch_price_internal")
    def test_get_stock_price_timeout(self, mock_fetch):
        """測試發生 Timeout 的情況"""
        # 讓內部方法直接拋出 TimeoutError 來模擬
        mock_fetch.side_effect = concurrent.futures.TimeoutError("Simulated Timeout")
        
        result = get_stock_price("2330")
        assert result is None
