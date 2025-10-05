# pip install fastmcp requests python-dotenv
import os
import time
import base64
import hmac
import hashlib
import urllib.parse
from typing import Optional, Literal, Union

import requests
from fastmcp import FastMCP
from dotenv import load_dotenv


load_dotenv()

TIME_PATH = "/0/public/Time"
SYSTEM_STATUS_PATH = "/0/public/SystemStatus"
ASSETS_PATH = "/0/public/Assets"
ASSET_PAIRS_PATH = "/0/public/AssetPairs"
TICKER_PATH = "/0/public/Ticker"
OHLC_PATH = "/0/public/OHLC"
DEPTH_PATH = "/0/public/Depth"
TRADES_PATH = "/0/public/Trades"
SPREAD_PATH = "/0/public/Spread"
KRAKEN_BASE = "https://api.kraken.com"
ADD_ORDER_PATH = "/0/private/AddOrder"
CANCEL_ORDER_PATH = "/0/private/CancelOrder"
OPEN_ORDERS_PATH = "/0/private/OpenOrders"
AMEND_ORDER_PATH = "/0/private/AmendOrder"
CANCEL_ALL_AFTER_PATH = "/0/private/CancelAllOrdersAfter"
BALANCE_PATH = "/0/private/Balance"
CLOSED_orders_PATH = "/0/private/ClosedOrders"
TRADES_HISTORY_PATH = "/0/private/TradesHistory"

API_KEY = os.getenv("KRAKEN_API_KEY")
API_SECRET = os.getenv("KRAKEN_API_SECRET")  # base64 string from Kraken

mcp = FastMCP("Kraken Pro MCP")

class KrakenError(RuntimeError):
    pass

def _require_keys():
    if not API_KEY or not API_SECRET:
        raise KrakenError(
            "Missing KRAKEN_API_KEY / KRAKEN_API_SECRET env vars."
        )

def _public_get(url_path: str, params: dict | None = None, timeout: float = 15.0) -> dict:
    """Helper for public endpoints (no auth)."""
    url = KRAKEN_BASE + url_path
    r = requests.get(url, params=params or {}, timeout=timeout)
    r.raise_for_status()
    j = r.json()
    if j.get("error"):
        raise KrakenError("; ".join(j["error"]))
    if "result" not in j:
        raise KrakenError("Kraken API response missing 'result' key.")
    return j["result"]

def _sign(url_path: str, payload: dict) -> str:
    """
    Kraken Spot REST signature:
    API-Sign = HMAC-SHA512( url_path + SHA256(nonce + postdata), base64_decode(secret) )
    Docs: https://docs.kraken.com/api/docs/guides/spot-rest-auth/
    """
    # urlencode payload for POST body
    postdata = urllib.parse.urlencode(payload)
    # nonce must be string + strictly increasing per key
    encoded = (str(payload["nonce"]) + postdata).encode()
    sha256 = hashlib.sha256(encoded).digest()
    message = url_path.encode() + sha256
    mac = hmac.new(base64.b64decode(API_SECRET), message, hashlib.sha512)
    return base64.b64encode(mac.digest()).decode(), postdata

def _private_post(url_path: str, data: dict, timeout: float = 15.0) -> dict:
    _require_keys()
    url = KRAKEN_BASE + url_path
    sig, postdata = _sign(url_path, data)
    headers = {
        "API-Key": API_KEY,
        "API-Sign": sig,
        "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
        "User-Agent": "fastmcp-kraken-pro/1.0",
    }
    r = requests.post(url, headers=headers, data=postdata, timeout=timeout)
    r.raise_for_status()
    j = r.json()
    if j.get("error"):
        raise KrakenError("; ".join(j["error"]))
    if "result" not in j:
        raise KrakenError("Kraken API response missing 'result' key.")
    return j["result"]

def _nonce() -> str:
    # millisecond nonce as string (strictly increasing per key)
    return str(int(time.time() * 1000))

#Trading API
@mcp.tool
def add_order(
    pair: str,
    side: Literal["buy", "sell"],
    ordertype: Literal[
        "market",
        "limit",
        "stop-loss",
        "take-profit",
        "stop-loss-limit",
        "take-profit-limit",
        "trailing-stop",
        "trailing-stop-limit",
    ] = "limit",
    volume: float = 0.0,
    price: Optional[str] = None,
    price2: Optional[str] = None,
    timeinforce: Optional[Literal["GTC", "IOC", "GTD"]] = None,
    userref: Optional[int] = None,
    cl_ord_id: Optional[str] = None,
    validate: bool = True,
) -> dict:
    """
    Place a new Kraken Spot order (REST AddOrder).

    NOTE: `validate=True` (default) will *not* execute the order; it only validates.
    Set `validate=False` to actually place the order.
    """
    data = {
        "nonce": _nonce(),
        "pair": pair,
        "type": side,
        "ordertype": ordertype,
        "volume": str(volume),
    }
    if price is not None:
        data["price"] = str(price)
    if price2 is not None:
        data["price2"] = str(price2)
    if timeinforce is not None:
        data["timeinforce"] = timeinforce  # GTC (default), IOC, GTD
    if userref is not None:
        data["userref"] = int(userref)
    if cl_ord_id is not None:
        data["cl_ord_id"] = cl_ord_id
    if validate:
        data["validate"] = True  # server checks but does not place

    return _private_post(ADD_ORDER_PATH, data)

@mcp.tool
def cancel_order(
    txid_or_userref: str,
) -> dict:
    """
    Cancel a particular open order (or set of orders).
    You can pass a Kraken order txid OR a userref (to cancel all with that userref).
    """
    data = {
        "nonce": _nonce(),
        "txid": txid_or_userref,
    }
    return _private_post(CANCEL_ORDER_PATH, data)

@mcp.tool
def open_orders(userref: Optional[int] = None, trades: bool = False) -> dict:
    """
    Fetch open orders. Optionally filter by userref and include `trades` detail.
    """
    data = {
        "nonce": _nonce(),
        "trades": bool(trades),
    }
    if userref is not None:
        data["userref"] = int(userref)
    return _private_post(OPEN_ORDERS_PATH, data)

@mcp.tool
def amend_order(
    order_id: Optional[str] = None,
    cl_ord_id: Optional[str] = None,
    order_qty: Optional[str] = None,      # e.g. "1.25"
    limit_price: Optional[str] = None,    # e.g. "69000.5"
    trigger_price: Optional[str] = None,  # for stop/TP orders
    display_qty: Optional[str] = None,    # iceberg display size
    post_only: Optional[bool] = None,     # reject if it would cross the book
) -> dict:
    """
    Atomic amend in-place (keeps identifiers & queue priority where possible).
    You MUST provide one identifier (order_id or cl_ord_id) and at least one
    amendable field (order_qty, limit_price, trigger_price, display_qty).
    """
    if not (order_id or cl_ord_id):
        raise KrakenError("Provide order_id or cl_ord_id.")
    if not any([order_qty, limit_price, trigger_price, display_qty]):
        raise KrakenError("Provide at least one field to amend.")

    data = {"nonce": _nonce()}
    if order_id is not None:
        data["order_id"] = order_id
    if cl_ord_id is not None:
        data["cl_ord_id"] = cl_ord_id
    if order_qty is not None:
        data["order_qty"] = str(order_qty)
    if limit_price is not None:
        data["limit_price"] = str(limit_price)
    if trigger_price is not None:
        data["trigger_price"] = str(trigger_price)
    if display_qty is not None:
        data["display_qty"] = str(display_qty)
    if post_only is not None:
        data["post_only"] = bool(post_only)

    return _private_post(AMEND_ORDER_PATH, data)

@mcp.tool
def cancel_all_orders_after(timeout_seconds: int) -> dict:
    """
    Dead man's switch: set countdown to cancel ALL your orders after `timeout_seconds`.
    Pass 0 to disable the switch.
    """
    data = {
        "nonce": _nonce(),
        "timeout": int(timeout_seconds),
    }
    return _private_post(CANCEL_ALL_AFTER_PATH, data)

# ------------------ Market Data tools ------------------

@mcp.tool
def server_time() -> dict:
    """Kraken server time (UTC)."""
    return _public_get(TIME_PATH)

@mcp.tool
def system_status() -> dict:
    """Current system status / trading mode."""
    return _public_get(SYSTEM_STATUS_PATH)

@mcp.tool
def asset_info(assets: str | None = None, aclass: str | None = None) -> dict:
    """
    Asset metadata. Example assets: 'XBT,ETH,USDT'
    aclass (optional): 'currency' (default) or other classes per Kraken.
    """
    params = {
        key: value
        for key, value in [("asset", assets), ("aclass", aclass)]
        if value is not None
    }
    return _public_get(ASSETS_PATH, params)

@mcp.tool
def tradable_asset_pairs(pairs: str | None = None, info: str | None = None) -> dict:
    """
    Tradable pairs & metadata. Example pairs: 'XBTUSD,ETHUSD'.
    info (optional): 'info', 'leverage', 'fees', 'margin', etc.
    """
    params = {
        key: value
        for key, value in [("pair", pairs), ("info", info)]
        if value is not None
    }
    return _public_get(ASSET_PAIRS_PATH, params)

@mcp.tool
def ticker(pairs: str | None = None) -> dict:
    """
    Level-1 ticker stats. Leave `pairs` None to get ALL.
    Example: 'XBTUSD,ETHUSD'
    """
    params = {}
    if pairs:
        params["pair"] = pairs
    return _public_get(TICKER_PATH, params)

@mcp.tool
def ohlc(pair: str, interval: int = 1, since: int | None = None) -> dict:
    """
    OHLC candles.
    interval (minutes): 1, 5, 15, 30, 60, 240, 1440, 10080, 21600
    since: optional Unix timestamp (seconds) or last id from a previous call.
    """
    params = {"pair": pair, "interval": int(interval)}
    if since is not None:
        params["since"] = int(since)
    return _public_get(OHLC_PATH, params)

@mcp.tool
def order_book(pair: str, count: int | None = None) -> dict:
    """
    L2 order book (aggregated per price level).
    count: optional max levels per side.
    """
    params = {"pair": pair}
    if count is not None:
        params["count"] = int(count)
    return _public_get(DEPTH_PATH, params)

@mcp.tool
def recent_trades(pair: str, since: int | None = None) -> dict:
    """
    Recent trades. Use the returned 'last' field as your next `since`.
    """
    params = {"pair": pair}
    if since is not None:
        params["since"] = int(since)
    return _public_get(TRADES_PATH, params)

@mcp.tool
def recent_spreads(pair: str, since: int | None = None) -> dict:
    """
    Recent top-of-book spreads (bid/ask).
    """
    params = {"pair": pair}
    if since is not None:
        params["since"] = int(since)
    return _public_get(SPREAD_PATH, params)


# ACCOUNT
@mcp.tool
def account_balance() -> dict:
    """
    Get Account Balance: all cash balances, net of pending withdrawals.
    """
    data = {"nonce": _nonce()}
    return _private_post(BALANCE_PATH, data)


@mcp.tool
def closed_orders(
    trades: bool = False,
    userref: Optional[int] = None,
    cl_ord_id: Optional[str] = None,
    start: Optional[Union[int, str]] = None,   # unix ts (sec) OR order txid
    end: Optional[Union[int, str]] = None,     # unix ts (sec) OR order txid
    ofs: Optional[int] = None,                 # pagination offset (50/page)
    closetime: Literal["open", "close", "both"] = "both",
    consolidate_taker: Optional[bool] = None,  # consolidate by taker trade
    without_count: bool = False,               # faster for many orders
    rebase_multiplier: Optional[str] = None,   # for tokenized assets (xstocks)
) -> dict:
    """
    Get Closed Orders (filled or cancelled). 50 results per page by default.
    """
    data = {
        "nonce": _nonce(),
        "trades": bool(trades),
        "closetime": closetime,
        "without_count": bool(without_count),
    }
    if userref is not None:
        data["userref"] = int(userref)
    if cl_ord_id is not None:
        data["cl_ord_id"] = cl_ord_id
    if start is not None:
        data["start"] = str(start)
    if end is not None:
        data["end"] = str(end)
    if ofs is not None:
        data["ofs"] = int(ofs)
    if consolidate_taker is not None:
        data["consolidate_taker"] = bool(consolidate_taker)
    if rebase_multiplier is not None:
        data["rebase_multiplier"] = rebase_multiplier

    return _private_post(CLOSED_orders_PATH, data)

@mcp.tool
def trades_history(
    type: Literal[
        "all",
        "any position",
        "closed position",
        "closing position",
        "no position",
    ] = "all",
    start: Optional[Union[int, str]] = None,  # unix ts (sec) OR trade txid
    end: Optional[Union[int, str]] = None,    # unix ts (sec) OR trade txid
    ofs: Optional[int] = None,                # pagination offset (50/page)
    consolidate_taker: Optional[bool] = None,
    ledgers: Optional[bool] = None,           # include related ledger IDs
    rebase_multiplier: Optional[str] = None,  # for tokenized assets (xstocks)
) -> dict:
    """
    Get Trades History (fills). 50 results per page, newest first.
    """
    data = {
        "nonce": _nonce(),
        "type": type,
    }
    if start is not None:
        data["start"] = str(start)
    if end is not None:
        data["end"] = str(end)
    if ofs is not None:
        data["ofs"] = int(ofs)
    if consolidate_taker is not None:
        data["consolidate_taker"] = bool(consolidate_taker)
    if ledgers is not None:
        data["ledgers"] = bool(ledgers)
    if rebase_multiplier is not None:
        data["rebase_multiplier"] = rebase_multiplier

    return _private_post(TRADES_HISTORY_PATH, data)

if __name__ == "__main__":
    mcp.run()
