"""
處理器測試
"""

from decimal import Decimal

from commands import alert_service, watch_service
from commands.handlers import dispatch_command
from commands.parser import parse_command

USER_ID = "U_test_handlers_user"


class TestHandlers:
    """測試 handlers.py 分派與執行邏輯。"""

    def _setup_watch(self, stock_code: str = "2330") -> None:
        watch_service.add_watch(USER_ID, stock_code)

    def test_clear_alerts_when_empty(self):
        # (1) 無警示時打「清空警示」回覆「你目前沒有警示」
        cmd = parse_command("清空警示")
        reply_text, quick_reply = dispatch_command(cmd, USER_ID)
        assert "你目前沒有警示" in reply_text
        assert quick_reply is None

    def test_clear_alerts_with_alerts(self):
        # (2) 有警示時完整打「清空警示 confirm」確實清空
        self._setup_watch("2330")
        alert_service.add_alert(USER_ID, "2330", "<", Decimal("1000"))

        # 第一段清空
        cmd_step1 = parse_command("清空警示")
        reply_text_step1, quick_reply_step1 = dispatch_command(cmd_step1, USER_ID)
        assert "確認清空請輸入：清空警示 confirm" in reply_text_step1
        assert quick_reply_step1 is None
        # 狀態應該還在（未清空）
        assert alert_service.count_alerts(USER_ID) == 1

        # 第二段清空（確認執行）
        cmd_step2 = parse_command("清空警示 confirm")
        reply_text_step2, quick_reply_step2 = dispatch_command(cmd_step2, USER_ID)
        assert "已清空所有警示" in reply_text_step2
        assert quick_reply_step2 is None
        # 確實清空
        assert alert_service.count_alerts(USER_ID) == 0

    def test_quick_reply_help_command(self):
        cmd = parse_command("幫助")
        reply_text, quick_reply = dispatch_command(cmd, USER_ID)
        assert quick_reply is not None
        assert len(quick_reply.items) == 3
        labels = [item.action.label for item in quick_reply.items]
        assert "查自選股" in labels
        assert "查警示清單" in labels
        assert "使用說明" in labels

    def test_quick_reply_list_watch(self):
        cmd = parse_command("自選")
        reply_text, quick_reply = dispatch_command(cmd, USER_ID)
        assert quick_reply is not None
        assert len(quick_reply.items) == 2
        labels = [item.action.label for item in quick_reply.items]
        assert "查警示清單" in labels
        assert "新增警示提示" in labels

    def test_quick_reply_list_alert(self):
        cmd = parse_command("警示清單")
        reply_text, quick_reply = dispatch_command(cmd, USER_ID)
        assert quick_reply is not None
        assert len(quick_reply.items) == 2
        labels = [item.action.label for item in quick_reply.items]
        assert "查自選股" in labels
        assert "清空警示" in labels

    def test_quick_reply_add_watch_success(self):
        cmd = parse_command("加自選 2330")
        reply_text, quick_reply = dispatch_command(cmd, USER_ID)
        assert "✅" in reply_text
        assert quick_reply is not None
        assert len(quick_reply.items) == 2
        labels = [item.action.label for item in quick_reply.items]
        assert "設定此股警示" in labels
        assert "查自選股" in labels
