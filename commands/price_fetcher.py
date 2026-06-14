"""
股價抓取服務層

提供獨立的股價查詢功能，並具備逾時控制與盤後資料（Fallback）的優雅處理機制。
"""

import concurrent.futures
import logging
from decimal import Decimal, InvalidOperation

import twstock

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 5

def _fetch_price_internal(stock_code: str) -> dict | None:
    """內部實際打 API 的邏輯，無 Timeout 控制。"""
    try:
        realtime_info = twstock.realtime.get(stock_code)
    except Exception as e:
        logger.warning(f"呼叫 twstock.realtime.get 時發生例外：{e}", exc_info=True)
        return None

    if not realtime_info or not realtime_info.get("success"):
        logger.warning(f"twstock 查詢失敗或查無股票：{stock_code}, 回傳內容：{realtime_info}")
        return None

    info = realtime_info.get("info", {})
    realtime = realtime_info.get("realtime", {})
    
    code = info.get("code")
    name = info.get("name")
    time_str = info.get("time")
    latest_price_str = realtime.get("latest_trade_price")
    
    # 判斷是否為有效即時價格
    is_realtime = True
    final_price_str = latest_price_str

    if final_price_str == "-" or not final_price_str:
        logger.info(f"股票 {stock_code} 無即時報價，嘗試降級抓取歷史收盤價。")
        is_realtime = False
        try:
            stock = twstock.Stock(stock_code)
            if stock.price and len(stock.price) > 0:
                final_price_str = str(stock.price[-1])
            else:
                logger.warning(f"股票 {stock_code} 無歷史收盤價可供降級。")
                return None
        except Exception as e:
            logger.warning(f"抓取股票 {stock_code} 歷史收盤價時發生例外：{e}", exc_info=True)
            return None

    try:
        price_decimal = Decimal(final_price_str).quantize(Decimal("0.01"))
    except InvalidOperation:
        logger.warning(f"股票 {stock_code} 的價格無法轉換為 Decimal：{final_price_str}")
        return None

    return {
        "code": code,
        "name": name,
        "price": price_decimal,
        "time": time_str,
        "is_realtime": is_realtime
    }


def get_stock_price(stock_code: str) -> dict | None:
    """
    獲取指定股票的價格資訊。
    
    具備逾時控制與盤後降級（Fallback）機制。
    
    Args:
        stock_code: 股票代號（例如 "2330"）
        
    Returns:
        包含股價資訊的字典，例如：
        {"code": "2330", "name": "台積電", "price": Decimal("1050.00"), "time": "...", "is_realtime": True}
        若查無資料或逾時則回傳 None。
    """
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_fetch_price_internal, stock_code)
            return future.result(timeout=TIMEOUT_SECONDS)
    except concurrent.futures.TimeoutError:
        logger.error(f"查詢股票 {stock_code} 逾時（超過 {TIMEOUT_SECONDS} 秒）。")
        return None
    except Exception as e:
        logger.error(f"查詢股票 {stock_code} 時發生未預期例外：{e}", exc_info=True)
        return None


if __name__ == "__main__":
    import sys
    # 設定基本的 logging 以便在 console 看到輸出
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    
    target_code = sys.argv[1] if len(sys.argv) > 1 else "2330"
    print(f"========== 測試股價抓取 ==========")
    print(f"目標股票代號: {target_code}")
    print(f"===================================")
    
    result = get_stock_price(target_code)
    
    if result:
        print("✅ 查詢成功：")
        for key, value in result.items():
            print(f"  - {key}: {repr(value)}")
    else:
        print("❌ 查詢失敗或查無此股票。")
