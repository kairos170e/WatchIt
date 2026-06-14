"""
市場交易時間判斷模組
"""

from datetime import datetime, time
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

def is_market_open(current_time: datetime | None = None) -> bool:
    """
    判斷當前時間是否為台股交易時段 (週一至週五 09:00 - 13:30)。
    
    Args:
        current_time: 可選的指定時間。預設為當下台北時間。
        
    Returns:
        若在交易時段內回傳 True，否則回傳 False。
    """
    tz = ZoneInfo("Asia/Taipei")
    if current_time is None:
        current_time = datetime.now(tz)
    else:
        # 確保有設定時區
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=tz)
        else:
            current_time = current_time.astimezone(tz)
            
    # 判斷是否為週末 (0: Monday, 6: Sunday)
    if current_time.weekday() >= 5:
        return False
        
    # 判斷是否在 09:00 - 13:30 之間
    market_start = time(9, 0)
    market_end = time(13, 30)
    
    current_time_only = current_time.time()
    
    if market_start <= current_time_only < market_end:
        return True
        
    return False
