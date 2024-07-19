from alpaca.trading.requests import GetAssetsRequest
from alpaca.trading.enums import AssetClass, AssetStatus, AssetExchange
from alpaca.trading.models import Asset

import yfinance as yf
import datetime
import json
from config import tradingClient
from tools import getHistoricalBars


def interesting(company: Asset):
    # TODO we might want to trade fractionable companies...
    return (
        company.status == AssetStatus.ACTIVE
        and company.tradable
        and company.shortable
        and company.easy_to_borrow
        and company.marginable
        and company.fractionable
    )


def marketCap(company: Asset):
    res = yf.Ticker(company.symbol).info.get("marketCap")
    return 0 if res is None else res


def symbolsStock() -> list[str]:
    """
    Retrieve US stock via yahoo finance.
    """
    print("Sorting by market cap")
    usCompanies = tradingClient.get_all_assets(
        GetAssetsRequest(asset_class=AssetClass.US_EQUITY)
    )
    companies: list[Asset] = list(filter(interesting, usCompanies))
    symbols = [company.symbol for company in companies]
    tickers = yf.Tickers(" ".join(symbols))
    MARKET_CAP = "marketCap"
    marketCaps = []
    for company in companies:
        symbol = company.symbol
        info = tickers.tickers[symbol].info
        if MARKET_CAP not in info:
            symbols.remove(symbol)
        else:
            marketCaps.append(info[MARKET_CAP])
    symbols = list(
        zip(*sorted(zip(symbols, marketCaps), key=lambda x: x[1], reverse=True))
    )[0]

    return symbols


def symbolsByVolume() -> list[str]:
    """
    Sort companies by volume trade
    """
    print("Sorting by daily volume trade")
    bars = getHistoricalBars(700)
    assert bars["next_page_token"] == None, "There is an unexpected next page token"
    bars = bars["bars"]
    symbols = sorted(bars.keys(), key=lambda symbol: bars[symbol][0]["v"], reverse=True)
    with open("companies.json", "w") as f:
        json.dump(symbols, f, indent=2)
    return symbols


def getTopCompanies() -> list[str]:
    """
    Dump every listed US companies in companies.json sorted by their market cap
    """
    symbols = symbolsStock()
    with open("companies.json", "w") as f:
        json.dump(symbols, f, indent=2)
    return symbols


def main():
    getTopCompanies()
    symbolsByVolume()


if __name__ == "__main__":
    main()
