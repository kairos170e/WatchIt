"""
使用者指令解析器

將 LINE 使用者傳入的文字訊息，轉換為結構化的 ParsedCommand 物件。
"""

import re
from decimal import Decimal, InvalidOperation
from re import Pattern

from commands.models import CommandType, ParsedCommand

# 台股代號：上市/上櫃多為 4 碼，ETF 等可能為 5～6 碼
STOCK_CODE_PATTERN = re.compile(r"^\d{4,6}$")

# 價格：正數、最多兩位小數
PRICE_PATTERN = re.compile(r"^\d+(?:\.\d{1,2})?$")

# 各指令的正則表達式（不分大小寫）
COMMAND_PATTERNS: list[tuple[CommandType, Pattern[str]]] = [
    # 說明 / 幫助
    (CommandType.HELP, re.compile(r"^(幫助|help|\?|說明|指令|h)$", re.IGNORECASE)),
    # 查詢股價：查詢 2330、查 台積電、q 2330
    (
        CommandType.QUERY,
        re.compile(r"^(查詢|查)\s*(.+)$|^(q|quote)\s+(.+)$", re.IGNORECASE),
    ),
    # 加入自選股
    (
        CommandType.ADD_WATCH,
        re.compile(r"^(加自選|加入|\+)\s*(.+)$|^(add)\s+(.+)$", re.IGNORECASE),
    ),
    # 移除自選股
    (
        CommandType.REMOVE_WATCH,
        re.compile(
            r"^(刪自選|移除|刪除|-)\s*(.+)$|^(remove|del)\s+(.+)$",
            re.IGNORECASE,
        ),
    ),
    # 自選股清單
    (
        CommandType.LIST_WATCH,
        re.compile(r"^(自選|清單|list|watchlist|watch)$", re.IGNORECASE),
    ),
]

# 警示相關指令 regex
ALERT_LIST_PATTERN = re.compile(r"^(警示清單|alert list|alerts)$", re.IGNORECASE)
CONFIRM_CLEAR_ALERTS_PATTERN = re.compile(r"^清空警示\s+confirm$", re.IGNORECASE)
CLEAR_ALERTS_PATTERN = re.compile(r"^清空警示$")
UPDATE_ALERT_PATTERN = re.compile(r"^改警示\s*(\d+)\s*([<>])\s*(\S+)$")
DELETE_ALERT_PATTERN = re.compile(r"^刪警示\s*(\d+)$")
ADD_ALERT_PATTERN = re.compile(r"^警示\s*(\d{4,6})\s*([<>])\s*(\S+)$")


def normalize_text(text: str) -> str:
    """
    正規化使用者輸入。

    - 去除前後空白
    - 全形數字轉半形（LINE 使用者常用手機全形鍵盤輸入數字）
    - 合併連續空白為單一空格

    Args:
        text: 原始文字。

    Returns:
        正規化後的文字。
    """
    normalized = text.strip()

    # 全形數字 ０-９ → 半形 0-9
    fullwidth_digits = "０１２３４５６７８９"
    for index, char in enumerate(fullwidth_digits):
        normalized = normalized.replace(char, str(index))

    # 合併多餘空白（例如「查詢  2330」）
    normalized = re.sub(r"\s+", " ", normalized)

    return normalized


def is_stock_code(value: str) -> bool:
    """
    判斷字串是否為台股代號格式。

    Args:
        value: 待檢查字串。

    Returns:
        符合 4～6 位數字格式時回傳 True。
    """
    return bool(STOCK_CODE_PATTERN.fullmatch(value))


def validate_price(price_str: str) -> Decimal | None:
    """
    驗證並轉換價格字串為 Decimal。

    規則：正數、最多兩位小數。

    Args:
        price_str: 價格字串，例如 "1000" 或 "99.50"。

    Returns:
        合法的 Decimal；格式不符或非正數時回傳 None。
    """
    if not PRICE_PATTERN.fullmatch(price_str):
        return None

    try:
        price = Decimal(price_str)
    except InvalidOperation:
        return None

    if price <= 0:
        return None

    # 正規化為兩位小數精度
    return price.quantize(Decimal("0.01"))


def extract_stock_target(raw_target: str) -> str:
    """
    從指令參數中提取股票標的。

    Args:
        raw_target: 指令後方的參數，例如「2330」或「台積電」。

    Returns:
        清理後的標的字串。
    """
    return raw_target.strip()


def _parse_alert_commands(normalized: str, raw_text: str) -> ParsedCommand | None:
    """
    解析警示相關指令。

    優先於一般指令比對，避免與其他模式衝突。

    Args:
        normalized: 正規化後的文字。
        raw_text: 使用者原始輸入。

    Returns:
        解析成功回傳 ParsedCommand；非警示指令回傳 None。
    """
    # 第二段確認（須優先於「清空警示」比對）
    if CONFIRM_CLEAR_ALERTS_PATTERN.match(normalized):
        return ParsedCommand(type=CommandType.CONFIRM_CLEAR_ALERTS, raw_text=raw_text)

    # 第一段：清空警示
    if CLEAR_ALERTS_PATTERN.match(normalized):
        return ParsedCommand(type=CommandType.CLEAR_ALERTS, raw_text=raw_text)

    # 警示清單
    if ALERT_LIST_PATTERN.match(normalized):
        return ParsedCommand(type=CommandType.LIST_ALERT, raw_text=raw_text)

    # 改警示 3 < 1050
    update_match = UPDATE_ALERT_PATTERN.match(normalized)
    if update_match:
        index = int(update_match.group(1))
        operator = update_match.group(2)
        price_str = update_match.group(3)
        price = validate_price(price_str)

        if index <= 0:
            return ParsedCommand(
                type=CommandType.UPDATE_ALERT,
                raw_text=raw_text,
                parse_error="❌ 警示序號必須為正整數。",
            )
        if price is None:
            return ParsedCommand(
                type=CommandType.UPDATE_ALERT,
                raw_text=raw_text,
                parse_error="❌ 價格格式不正確。請輸入正數，最多兩位小數。",
            )

        return ParsedCommand(
            type=CommandType.UPDATE_ALERT,
            raw_text=raw_text,
            alert_index=index,
            operator=operator,
            target_price=price,
        )

    # 刪警示 3
    delete_match = DELETE_ALERT_PATTERN.match(normalized)
    if delete_match:
        index = int(delete_match.group(1))
        if index <= 0:
            return ParsedCommand(
                type=CommandType.DELETE_ALERT,
                raw_text=raw_text,
                parse_error="❌ 警示序號必須為正整數。",
            )
        return ParsedCommand(
            type=CommandType.DELETE_ALERT,
            raw_text=raw_text,
            alert_index=index,
        )

    # 警示 2330 < 1000
    add_match = ADD_ALERT_PATTERN.match(normalized)
    if add_match:
        stock_code = add_match.group(1)
        operator = add_match.group(2)
        price_str = add_match.group(3)
        price = validate_price(price_str)

        if not is_stock_code(stock_code):
            return ParsedCommand(
                type=CommandType.ADD_ALERT,
                raw_text=raw_text,
                parse_error="❌ 股票代號格式不正確。請輸入 4～6 位數字代號。",
            )
        if price is None:
            return ParsedCommand(
                type=CommandType.ADD_ALERT,
                raw_text=raw_text,
                parse_error="❌ 價格格式不正確。請輸入正數，最多兩位小數。",
            )

        return ParsedCommand(
            type=CommandType.ADD_ALERT,
            raw_text=raw_text,
            target=stock_code,
            operator=operator,
            target_price=price,
        )

    return None


def parse_command(text: str) -> ParsedCommand:
    """
    解析使用者文字訊息為結構化指令。

    解析優先順序：
      1. 警示相關指令
      2. 已知指令前綴（幫助、查詢、加自選…）
      3. 若整段文字為純數字代號 → 視為查詢
      4. 其餘 → UNKNOWN

    Args:
        text: 使用者原始輸入。

    Returns:
        ParsedCommand 物件。
    """
    normalized = normalize_text(text)

    # 空訊息
    if not normalized:
        return ParsedCommand(type=CommandType.UNKNOWN, raw_text=text)

    # 警示指令（優先）
    alert_command = _parse_alert_commands(normalized, text)
    if alert_command is not None:
        return alert_command

    # 依序比對一般指令模式
    for command_type, pattern in COMMAND_PATTERNS:
        match = pattern.match(normalized)
        if not match:
            continue

        # HELP / LIST_WATCH 等無參數指令
        if command_type in (CommandType.HELP, CommandType.LIST_WATCH):
            return ParsedCommand(type=command_type, raw_text=text)

        # 有參數的指令：取最後一個 capture group 作為 target
        target = extract_stock_target(match.group(match.lastindex or 1))
        return ParsedCommand(
            type=command_type,
            raw_text=text,
            target=target,
        )

    # 直接輸入代號（例如「2330」）→ 查詢
    if is_stock_code(normalized):
        return ParsedCommand(
            type=CommandType.QUERY,
            raw_text=text,
            target=normalized,
        )

    # 無法辨識
    return ParsedCommand(type=CommandType.UNKNOWN, raw_text=text)
