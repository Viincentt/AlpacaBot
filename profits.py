from collections import defaultdict
import datetime
import json

from tools import getAllOrder

SYMBOL = "symbol"
CANCELED_AT = "canceled_at"
SIDE = "side"
QTY = "filled_qty"
PRICE = "filled_avg_price"


def percentagePnl(trades):
    # Dictionaries to store net PnL and initial investment by company
    totalBuy = defaultdict(float)
    totalSell = defaultdict(float)
    qtys = defaultdict(int)
    for trade in trades[::-1]:
        symbol, qty = trade[SYMBOL], int(trade[QTY])
        if qty == 0:
            continue
        amount = qty * float(trade[PRICE])
        if trade[SIDE] == "buy":
            totalBuy[symbol] += amount
            qtys[symbol] += qty
        else:
            totalSell[symbol] += amount
            qtys[symbol] -= qty

    for symbol, value in qtys.items():
        if value != 0:
            print(symbol, "outstanding", value, "stock(s)")
            totalBuy.pop(symbol, None)
            totalSell.pop(symbol, None)

    # Calculate percentage PnL for each company
    percentagePnl = defaultdict(float)
    for symbol in totalBuy:
        cost, gain = totalBuy[symbol], totalSell[symbol]
        assert cost != 0, f"{symbol} cost 0"
        percentagePnl[symbol] = round(((gain - cost) / cost) * 100, 2)

    return percentagePnl


def main():
    orders = getAllOrder()
    res = {}
    percentPnl = dict(sorted(percentagePnl(orders).items(), key=lambda item: item[1]))
    for company in percentPnl:
        res[company] = {"pnl": percentPnl[company], "comments": ""}
    ORDERS = "orders"
    for order in orders:
        company = order[SYMBOL]
        if company not in res or int(order[QTY]) == 0:
            continue
        if ORDERS not in res[company]:
            res[company][ORDERS] = {}
        res[company][ORDERS][
            len(res[company][ORDERS])
        ] = f"{order['submitted_at']} {order[SIDE]} at {order[PRICE]}"
    today = datetime.date.today()
    with open(f"profits/profits_{today}.json", "w") as f:
        json.dump(res, f, indent=2)


if __name__ == "__main__":
    main()
