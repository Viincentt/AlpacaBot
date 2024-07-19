import datetime
import json
import math
import time
import requests

from typing import Literal
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import TimeInForce, AssetClass, OrderSide, OrderType
from alpaca.trading.models import Asset
from alpaca.trading.requests import GetAssetsRequest, OrderRequest

from config import API_ID, API_KEY

timeInForce = Literal[
    TimeInForce.DAY,
    TimeInForce.FOK,  # Fill or Kill
    TimeInForce.GTC,  # Good till canceled
    TimeInForce.IOC,  # Immediate or cancel
    TimeInForce.OPG,  # On market opening
    TimeInForce.CLS,  # On market closing
]

orderSideStr = {OrderSide.BUY: "BUY", OrderSide.SELL: "SELL"}
orderTypeStr = {
    OrderType.TRAILING_STOP: "TRAILING STOP",
    OrderType.STOP: "STOP",
    OrderType.STOP_LIMIT: "STOP LIMIT",
    OrderType.MARKET: "MARKET",
    OrderType.LIMIT: "LIMIT",
}

headers = {
    "accept": "application/json",
    "APCA-API-KEY-ID": API_ID,
    "APCA-API-SECRET-KEY": API_KEY,
}


def roundDown2Decimals(n: float) -> float:
    """
    Return the number rounded down to 2 decimals.
    """
    return n // 0.01 / 100


def roundUp2Decimals(n: float) -> float:
    """
    Return the number rounded up to 2 decimals.
    """
    return math.ceil(n * 100) / 100


def liquidateAllPositions(client: TradingClient):
    client.close_all_positions()


def cancelAllOrders(client: TradingClient):
    client.cancel_orders()


def cancelAllOrdersAndLiquidatePositions(client: TradingClient):
    cancelAllOrders(client)
    liquidateAllPositions(client)


def getTopNCompanies(n: int = 400) -> list[str]:
    with open("companies.json", "r") as f:
        return json.load(f)[:n]


def getEquity(client: TradingClient, buyingPower: bool = False):
    if buyingPower:
        return float(client.get_account().buying_power)
    return float(client.get_account().equity)


def submit(client: TradingClient, order: OrderRequest):
    return client.submit_order(order)


def waitForMarketOpening():
    """
    Sleeps until the US market opens
    """
    print("waiting for market opening")
    sleepUntil(14, 29, 58)
    print("market opening soon, listening...")


def sleepUntil(hour: int, minute: int, second: int = 0):
    now = datetime.datetime.now()
    target_time = now.replace(hour=hour, minute=minute, second=second, microsecond=0)

    # If target time is in the past for today, set the target to the same time tomorrow
    if target_time <= now:
        return
        target_time += datetime.timedelta(days=1)

    sleep_duration = (target_time - now).total_seconds()
    time.sleep(sleep_duration)


def getLatestTrades(companies, feed="sip"):
    # TODO change feed to sip if we get real time market
    comps = "%2C".join(companies)
    url = f"https://data.alpaca.markets/v2/stocks/trades/latest?symbols={comps}&feed={feed}"
    return requests.get(url, headers=headers).json()


def getAllOrder(date=None):
    if date == None:
        now = datetime.datetime.now()
        cutoff_time = now.replace(hour=14, minute=30, second=0, microsecond=0)
        today = datetime.date.today()
        # get trades from today or yesterday if market has not opened yet
        date = today
        if now < cutoff_time:
            date -= datetime.timedelta(days=1)
    start = str(date) + "T00:01:00Z"
    end = str(date) + "T23:59:59Z"
    res = []
    url = f"https://paper-api.alpaca.markets/v2/orders?status=closed&limit=500"

    while orders := requests.get(
        url + f"&after={start}&until={end}&direction=asc", headers=headers
    ).json():
        if len(orders) == 1:
            res += orders
            break
        res += orders[:-1]
        start = orders[-1]["submitted_at"]
    return res


def getHistoricalBars(n: int = 10000):
    with open("companies.json", "r") as f:
        symbols = json.load(f)[:n]
    url = "https://data.alpaca.markets/v2/stocks/bars?"

    url += "symbols="
    url += "%2C".join(symbols)
    url += "&timeframe=1D"
    now = datetime.datetime.now()
    cutoff_time = now.replace(hour=14, minute=30, second=0, microsecond=0)
    if now < cutoff_time:
        yesterday = datetime.date.today() - datetime.timedelta(days=2)
        url += f"&start={yesterday}"
    url += "&limit=10000&adjustment=raw&feed=sip&sort=asc"
    return requests.get(url, headers=headers).json()
