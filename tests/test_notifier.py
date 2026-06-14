"""
測試推播通知服務
"""

from decimal import Decimal
from unittest.mock import MagicMock

from commands.notifier import push_alert_notification


class TestNotifier:
    def test_push_alert_notification_success(self):
        mock_messaging_api = MagicMock()
        
        result = push_alert_notification(
            messaging_api=mock_messaging_api,
            line_user_id="U123456789",
            stock_code="2330",
            stock_name="台積電",
            operator=">",
            target_price=Decimal("1000"),
            current_price=Decimal("1050"),
            time_str="2026-06-15 10:00:00",
            is_realtime=True,
        )
        
        assert result is True
        mock_messaging_api.push_message.assert_called_once()
        args, _ = mock_messaging_api.push_message.call_args
        push_req = args[0]
        assert push_req.to == "U123456789"
        assert len(push_req.messages) == 1
        text_content = push_req.messages[0].text
        assert "2330 台積電" in text_content
        assert "1050" in text_content
        assert "大於等於 1000" in text_content
        assert "非即時報價" not in text_content

    def test_push_alert_notification_not_realtime(self):
        mock_messaging_api = MagicMock()
        
        result = push_alert_notification(
            messaging_api=mock_messaging_api,
            line_user_id="U123456789",
            stock_code="2330",
            stock_name="台積電",
            operator=">",
            target_price=Decimal("1000"),
            current_price=Decimal("1050"),
            time_str="2026-06-15 13:30:00",
            is_realtime=False,
        )
        
        assert result is True
        args, _ = mock_messaging_api.push_message.call_args
        push_req = args[0]
        text_content = push_req.messages[0].text
        assert "非即時報價" in text_content

    def test_push_alert_notification_exception(self):
        mock_messaging_api = MagicMock()
        mock_messaging_api.push_message.side_effect = Exception("Simulated API Error")
        
        result = push_alert_notification(
            messaging_api=mock_messaging_api,
            line_user_id="U123456789",
            stock_code="2330",
            stock_name="台積電",
            operator="<",
            target_price=Decimal("1000"),
            current_price=Decimal("950"),
            time_str="2026-06-15 10:00:00",
        )
        
        assert result is False
        mock_messaging_api.push_message.assert_called_once()
