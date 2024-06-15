import time
import pandas as pd

from utils import Tick, TRADE_BAR_PROPERTIES

from ibapi.client import EClient


class IBClient(EClient):
    def __init__(self, wrapper):
        EClient.__init__(self, wrapper)

    def cancel_all_orders(self):
        self.reqGlobalCancel()

    def cancel_order_by_id(self, order_id):
        self.cancelOrder(orderId=order_id, manualCancelOrderTime="")

    def update_order(self, contract, order, order_id):
        self.cancel_order_by_id(order_id)
        return self.send_order(contract, order)

    def send_order(self, contract, order):
        order_id = self.wrapper.nextValidOrderId
        self.placeOrder(orderId=order_id, contract=contract, order=order)
        self.reqIds(-1)
        return order_id

    def get_historical_data(self, request_id, contract, duration, bar_size):
        self.reqHistoricalData(
            reqId=request_id,
            contract=contract,
            endDateTime="",
            durationStr=duration,
            barSizeSetting=bar_size,
            whatToShow="MIDPOINT",
            useRTH=1,
            formatDate=1,
            keepUpToDate=False,
            chartOptions=[],
        )
        time.sleep(5)

        bar_sizes = ["day", "D", "week", "W", "month"]
        if any(x in bar_size for x in bar_sizes):
            fmt = "%Y%m%d"
        else:
            fmt = "%Y%m%d %H:%M:%S %Z"

        data = self.historical_data[request_id]

        df = pd.DataFrame(data, columns=TRADE_BAR_PROPERTIES)
        df.set_index(pd.to_datetime(df.time, format=fmt), inplace=True)
        df.drop("time", axis=1, inplace=True)
        df["symbol"] = contract.symbol
        df.request_id = request_id

        return df

    def get_historical_data_for_many(
        self, request_id, contracts, duration, bar_size, col_to_use="close"
    ):
        dfs = []
        for contract in contracts:
            data = self.get_historical_data(request_id, contract, duration, bar_size)
            dfs.append(data)
            request_id += 1
        return (
            pd.concat(dfs)
            .reset_index()
            .pivot(index="time", columns="symbol", values=col_to_use)
        )

    def get_market_data(self, request_id, contract, tick_type=4):
        self.reqMktData(
            reqId=request_id,
            contract=contract,
            genericTickList="4",
            snapshot=True,
            regulatorySnapshot=False,
            mktDataOptions=[],
        )
        time.sleep(5)

        self.cancelMktData(reqId=request_id)

        return self.market_data[request_id][tick_type]
        return self.market_data[request_id][tick_type]

    def get_streaming_data(self, request_id, contract):
        self.reqTickByTickData(
            reqId=request_id,
            contract=contract,
            tickType="BidAsk",
            numberOfTicks=0,
            ignoreSize=True,
        )
        time.sleep(10)

        while True:
            if self.stream_event.is_set():
                yield Tick(*self.streaming_data[request_id])
                self.stream_event.clear()

    def stop_streaming_data(self, request_id):
        self.cancelTickByTickData(reqId=request_id)

    def get_account_values(self, key=None):
        self.reqAccountUpdates(True, self.account)
        time.sleep(2)
        if key:
            return self.account_values[key]
        return self.account_values

    def get_positions(self):
        self.reqAccountUpdates(True, self.account)
        time.sleep(2)
        return self.positions

    def get_pnl(self, request_id):
        self.reqPnL(request_id, self.account, "")
        time.sleep(2)
        self.cancelPnL(reqId=request_id)
        return self.account_pnl

    def get_streaming_pnl(self, request_id, interval=60, pnl_type="unrealized_pnl"):
        interval = max(interval, 5) - 2
        while True:
            pnl = self.get_pnl(request_id=request_id)
            yield {"date": pd.Timestamp.now(), "pnl": pnl[request_id].get(pnl_type)}
            time.sleep(interval)

    def get_streaming_returns(self, request_id, interval, pnl_type):
        returns = pd.Series(dtype=float)
        for snapshot in self.get_streaming_pnl(
            request_id=request_id, interval=interval, pnl_type=pnl_type
        ):
            returns.loc[snapshot["date"]] = snapshot["pnl"]
            if len(returns) > 1:
                self.portfolio_returns = returns.pct_change().dropna()
