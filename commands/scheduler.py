"""
排程器模組

負責定期抓取未觸發的警示股票即時價格，比對後推播通知。
"""

import logging
import os
import time
from collections import defaultdict

from apscheduler.schedulers.background import BackgroundScheduler
from linebot.v3.messaging import MessagingApi

from commands.database import get_session
from commands.db_models import Alert
from commands.market_hours import is_market_open
from commands.notifier import push_alert_notification
from commands.price_fetcher import get_stock_price

logger = logging.getLogger(__name__)

# 全域 scheduler 實例
_scheduler: BackgroundScheduler | None = None

def check_alerts_job(messaging_api: MessagingApi):
    """
    排程執行的主要檢查工作。
    """
    if os.environ.get("FORCE_MARKET_OPEN") == "true":
        logger.info("測試模式：強制繞過時段判斷")
    elif not is_market_open():
        logger.info("非交易時段，略過警示檢查。")
        return

    logger.info("開始執行警示檢查。")
    
    try:
        with get_session() as session:
            # 取得所有未觸發的警示
            alerts = session.query(Alert).filter(Alert.is_triggered == False).all()
            
            if not alerts:
                logger.info("目前沒有待檢查的警示。")
                return
                
            # 將警示依股票代號分組，避免重複查詢同一檔股票
            alerts_by_stock = defaultdict(list)
            for alert in alerts:
                alerts_by_stock[alert.stock_code].append(alert)
                
            for stock_code, stock_alerts in alerts_by_stock.items():
                logger.info(f"正在查詢股票 {stock_code} 的即時價格...")
                price_info = get_stock_price(stock_code)
                
                # 為了避免被證交所限流，稍微暫停
                time.sleep(0.5)
                
                if not price_info:
                    logger.warning(f"無法取得 {stock_code} 的價格，略過此次檢查。")
                    continue
                    
                current_price = price_info["price"]
                stock_name = price_info.get("name", "未知")
                time_str = price_info.get("time", "")
                is_realtime = price_info.get("is_realtime", True)
                
                # 檢查該股票的所有待觸發警示
                for alert in stock_alerts:
                    is_hit = False
                    if alert.operator == ">" and current_price >= alert.target_price:
                        is_hit = True
                    elif alert.operator == "<" and current_price <= alert.target_price:
                        is_hit = True
                        
                    if is_hit:
                        logger.info(f"警示觸發！股票 {stock_code} 條件 {alert.operator} {alert.target_price}，當前 {current_price}")
                        
                        # 呼叫推播
                        push_success = push_alert_notification(
                            messaging_api=messaging_api,
                            line_user_id=alert.line_user_id,
                            stock_code=stock_code,
                            stock_name=stock_name,
                            operator=alert.operator,
                            target_price=alert.target_price,
                            current_price=current_price,
                            time_str=time_str,
                            is_realtime=is_realtime,
                        )
                        
                        if push_success:
                            # 只有推播成功才標記為已觸發
                            alert.is_triggered = True
                            session.commit()
                            logger.info(f"警示 ID {alert.id} 已標記為觸發。")
                        else:
                            logger.warning(f"警示 ID {alert.id} 推播失敗，保留未觸發狀態等待下次重試。")
                            
    except Exception as e:
        logger.exception(f"執行警示檢查迴圈時發生未預期例外：{e}")


def start_scheduler(messaging_api: MessagingApi, interval_minutes: int = 5):
    """
    初始化並啟動背景排程器。
    
    Args:
        messaging_api: LINE Messaging API 實例。
        interval_minutes: 檢查間隔分鐘數。
    """
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        logger.warning("Scheduler 已經在運行中。")
        return

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        check_alerts_job,
        trigger="interval",
        minutes=interval_minutes,
        args=[messaging_api],
        id="check_alerts_job",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info(f"警示檢查排程器已啟動，每 {interval_minutes} 分鐘執行一次。")


def shutdown_scheduler():
    """
    優雅關閉背景排程器。
    """
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("警示檢查排程器已關閉。")
        _scheduler = None
