"""
測試排程器邏輯
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

from commands.db_models import Alert
from commands.scheduler import check_alerts_job


class TestScheduler:
    @patch("commands.scheduler.is_market_open")
    def test_market_closed(self, mock_is_market_open):
        """測試非交易時段直接跳過"""
        mock_is_market_open.return_value = False
        mock_api = MagicMock()
        
        with patch("commands.scheduler.get_session") as mock_db:
            check_alerts_job(mock_api)
            mock_db.assert_not_called()

    @patch("commands.scheduler.time.sleep")
    @patch("commands.scheduler.is_market_open")
    @patch("commands.scheduler.push_alert_notification")
    @patch("commands.scheduler.get_stock_price")
    @patch("commands.scheduler.get_session")
    def test_check_alerts_job_triggered_and_success(
        self, mock_get_session, mock_get_stock_price, mock_push, mock_is_market_open, mock_sleep
    ):
        """測試盤中條件達成且推播成功，更新為已觸發"""
        mock_is_market_open.return_value = True
        
        # 模擬資料庫
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        alert1 = Alert(id=1, line_user_id="U1", stock_code="2330", operator=">", target_price=Decimal("1000"), is_triggered=False)
        alert2 = Alert(id=2, line_user_id="U1", stock_code="2330", operator="<", target_price=Decimal("900"), is_triggered=False)
        
        # mock 查詢回傳
        mock_query = mock_session.query.return_value.filter.return_value
        mock_query.all.return_value = [alert1, alert2]
        
        # mock 查價
        mock_get_stock_price.return_value = {
            "price": Decimal("1050"),
            "name": "台積電",
            "time": "2026-06-15 10:00:00"
        }
        
        # mock 推播成功
        mock_push.return_value = True
        
        mock_api = MagicMock()
        check_alerts_job(mock_api)
        
        # 檢查查價呼叫
        mock_get_stock_price.assert_called_once_with("2330")
        
        # 檢查推播呼叫（只有 alert1 > 1000 會觸發，alert2 < 900 不會）
        mock_push.assert_called_once_with(
            messaging_api=mock_api,
            line_user_id="U1",
            stock_code="2330",
            stock_name="台積電",
            operator=">",
            target_price=Decimal("1000"),
            current_price=Decimal("1050"),
            time_str="2026-06-15 10:00:00",
            is_realtime=True,
        )
        
        # 檢查標記更新
        assert alert1.is_triggered is True
        assert alert2.is_triggered is False
        mock_session.commit.assert_called()

    @patch("commands.scheduler.time.sleep")
    @patch("commands.scheduler.is_market_open")
    @patch("commands.scheduler.push_alert_notification")
    @patch("commands.scheduler.get_stock_price")
    @patch("commands.scheduler.get_session")
    def test_check_alerts_job_push_failed(
        self, mock_get_session, mock_get_stock_price, mock_push, mock_is_market_open, mock_sleep
    ):
        """測試盤中條件達成但推播失敗，不更新狀態"""
        mock_is_market_open.return_value = True
        
        # 模擬資料庫
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        alert1 = Alert(id=1, line_user_id="U1", stock_code="2330", operator=">", target_price=Decimal("1000"), is_triggered=False)
        
        mock_query = mock_session.query.return_value.filter.return_value
        mock_query.all.return_value = [alert1]
        
        mock_get_stock_price.return_value = {
            "price": Decimal("1050"),
            "name": "台積電",
            "time": "2026-06-15 10:00:00"
        }
        
        # mock 推播失敗
        mock_push.return_value = False
        
        mock_api = MagicMock()
        check_alerts_job(mock_api)
        
        # 檢查標記未更新
        assert alert1.is_triggered is False
        mock_session.commit.assert_not_called()
