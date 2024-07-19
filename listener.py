from datetime import datetime
from alpaca.trading.models import TradeUpdate, Order
from alpaca.trading.enums import OrderStatus, OrderType, OrderSide, TimeInForce
from alpaca.trading.requests import TrailingStopOrderRequest
from config import tradingStream, tradingClient
from tools import submit, orderSideStr, orderTypeStr, waitForMarketOpening


async def on_msg(data: TradeUpdate):
    order: Order = data.order
    if order.status in [
        OrderStatus.FILLED,
        OrderStatus.PARTIALLY_FILLED,
    ]:
        if order.order_type in [OrderType.STOP, OrderType.STOP_LIMIT, OrderType.MARKET]:
            side = OrderSide.SELL if order.side == OrderSide.BUY else OrderSide.BUY
            trailingStopLossRequest = TrailingStopOrderRequest(
                symbol=order.symbol,
                qty=data.qty,
                side=side,
                time_in_force=TimeInForce.GTC,
                trail_percent=1.5,  # 98.5%  # 99.9% IS THE MINIMUM
            )
            submit(tradingClient, trailingStopLossRequest)
        print(
            datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            orderTypeStr[order.type],
            orderSideStr[order.side],
            data.qty,
            order.symbol,
            order.filled_avg_price,
            order.status,
        )


def main():
    tradingStream.subscribe_trade_updates(on_msg)
    waitForMarketOpening()
    tradingStream.run()


if __name__ == "__main__":
    main()
