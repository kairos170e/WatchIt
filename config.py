"""
Watch It - 設定模組

負責從 .env 載入環境變數，並提供給 Flask 應用程式與 LINE SDK 使用。
"""

import os

from dotenv import load_dotenv

# 從專案根目錄的 .env 檔案載入環境變數（若不存在則略過，改讀系統環境變數）
load_dotenv()


class Config:
    """應用程式設定類別，集中管理所有環境變數。"""

    # LINE Messaging API 憑證
    LINE_CHANNEL_ACCESS_TOKEN: str | None = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
    LINE_CHANNEL_SECRET: str | None = os.getenv("LINE_CHANNEL_SECRET")

    # Flask 伺服器設定
    FLASK_HOST: str = os.getenv("FLASK_HOST", "0.0.0.0")
    FLASK_PORT: int = int(os.getenv("FLASK_PORT", "5000"))
    FLASK_DEBUG: bool = os.getenv("FLASK_DEBUG", "False").lower() in (
        "true",
        "1",
        "yes",
    )

    @classmethod
    def validate(cls) -> None:
        """
        啟動前驗證必要環境變數是否已設定。

        Raises:
            ValueError: 當 LINE 憑證缺失時拋出，避免 Bot 以不完整設定啟動。
        """
        missing: list[str] = []

        if not cls.LINE_CHANNEL_ACCESS_TOKEN:
            missing.append("LINE_CHANNEL_ACCESS_TOKEN")
        if not cls.LINE_CHANNEL_SECRET:
            missing.append("LINE_CHANNEL_SECRET")

        if missing:
            raise ValueError(
                f"缺少必要環境變數：{', '.join(missing)}。"
                "請複製 .env.example 為 .env 並填入正確的 LINE 憑證。"
            )
