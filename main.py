import concurrent.futures
import requests
import time as tm
import os
from datetime import datetime, time
from alpaca.data.requests import StockLatestBarRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass
from alpaca.trading.models import Asset
from alpaca.trading.requests import (
    MarketOrderRequest,
    StopOrderRequest,
    StopLimitOrderRequest,
)
from config import API_ID, API_KEY, tradingClient
from tools import (
    roundUp2Decimals,
    submit,
    getTopNCompanies,
    sleepUntil,
    getLatestTrades,
    getEquity,
    roundDown2Decimals,
    orderSideStr,
    waitForMarketOpening,
)


def run():
    # 0.9%      , -1.5%
    buyThreshold, sellThreshold = 1 + 0.009, 1 - 0.015
    # Polling interval in seconds.
    sleepTime = 0.1
    d, maxWorkers, finished = {}, os.cpu_count(), 0
    minPrice, maxPrice = "minPrice", "maxPrice"
    firstMin, firstMax = "firstMin", "firstMax"
    lastPrice, lastId, trades, traded = "lastPrice", "lastId", "trades", "traded"

    # 200 companies takes the same time as 10 companies for requests.get
    symbols = getTopNCompanies()
    amount = getEquity(tradingClient, buyingPower=True) / len(symbols)

    def process(symbol: str, trade) -> int:
        done, curId, price = 0, trade["i"], trade["p"]

        if d[symbol][traded] or curId == d[symbol][lastId]:
            return done

        # wait until market is opened
        if d[symbol][minPrice] == -1:
            if datetime.now().time() >= time(14, 30):
                d[symbol][minPrice], d[symbol][maxPrice] = price, price
            else:
                return done

        d[symbol][maxPrice] = max(price, d[symbol][maxPrice])
        d[symbol][minPrice] = min(price, d[symbol][minPrice])

        # wait for the first minute and collect first candle max/min
        if d[symbol][firstMin] == -1:
            if datetime.now().time() >= time(14, 31):
                d[symbol][firstMin] = d[symbol][minPrice]
                d[symbol][firstMax] = d[symbol][maxPrice]
            else:
                return done

        d[symbol][lastId] = curId
        d[symbol][lastPrice] = price

        if d[symbol][lastPrice] <= amount:
            if price >= d[symbol][minPrice] * buyThreshold:
                # TODO maybe we only need to check price > minPrice but im too drunk now
                if price <= d[symbol][maxPrice] * sellThreshold:
                    print(symbol, "really volatile, can buy or sell")
                    d[symbol][traded] = True
                    done += 1
                    return done
                if d[symbol][minPrice] < d[symbol][firstMin]:
                    print(symbol, "tried buying but price went below first minute min")
                    d[symbol][traded] = True
                    done += 1
                    return done
                # if price < firstMax: return done
                side = OrderSide.BUY
            elif price <= d[symbol][maxPrice] * sellThreshold:
                if d[symbol][maxPrice] > d[symbol][firstMax]:
                    print(symbol, "tried selling but price went above first minute max")
                    d[symbol][traded] = True
                    done += 1
                    return done
                side = OrderSide.SELL
            else:
                return done
            qty = amount // price
            order = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=side,
                time_in_force=TimeInForce.IOC,
                order_class=OrderClass.SIMPLE,
            )
            submit(tradingClient, order)
            print(
                datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                orderSideStr[side],
                qty,
                symbol,
                price,
            )
            d[symbol][traded] = True
            done += 1
        return done

    response = getLatestTrades(symbols)
    for symbol, trade in response[trades].items():
        """
        - DONE entering too late -> buy membership to have latest price
        - leaving TLS not good enough losing too much with stop order
            - DONE trading only high volume stock might resolve this issue.
            - create a bot that look at position and unrealized profit; market sale when it is too low
                - advantage of this we can set up a hard stop loss like (no loss -0%) and lock in whatever profit - x%
        """
        d[symbol] = {
            traded: False,
            firstMin: -1,
            firstMax: -1,
            minPrice: -1,
            maxPrice: -1,
            lastPrice: trade["p"],
            lastId: trade["i"],
        }
    waitForMarketOpening()
    while finished < len(symbols) and datetime.now().time() < time(15):
        response = getLatestTrades(symbols)
        # Run the tasks concurrently because each company is independant.
        with concurrent.futures.ThreadPoolExecutor(max_workers=maxWorkers) as executor:
            # We dont need to wait to finish processing first company to start processing last company
            # Submit all tasks to the executor
            futures = [
                executor.submit(process, symbol, trade)
                for symbol, trade in response[trades].items()
            ]
            # Optionally, wait for all futures to complete
            finished += sum(
                future.result() for future in concurrent.futures.as_completed(futures)
            )

        """
        print(datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "1 loop finished")
        I would like to see when to stop trading ie when the volatility is less
        if now > deadlineTakingPosition:
            for symbol in symbols:
                d[symbol][traded] = 1
        """
        tm.sleep(sleepTime)


def main():
    run()


if __name__ == "__main__":
    main()
