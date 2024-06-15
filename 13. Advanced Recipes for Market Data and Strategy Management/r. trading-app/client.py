import time
import pandas as pd

from utils import (
    Tick,
    TRADE_BAR_PROPERTIES,
    DEFAULT_MARKET_DATA_ID,
    DEFAULT_CONTRACT_ID,
)
from order import BUY, SELL

from ibapi.client import EClient


class IBClient(EClient):
    def __init__(self, wrapper):
        EClient.__init__(self, wrapper)

    def resolve_contract(self, contract, request_id=DEFAULT_CONTRACT_ID):
        self.reqContractDetails(reqId=request_id, contract=contract)
        time.sleep(2)
        self.contractDetailsEnd(reqId=request_id)
        return self.resolved_contract

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

    def order_value(self, contract, order_type, value, **kwargs):
        # Place an order for a fixed amount of money.
        quantity = self._calculate_order_value_quantity(contract, value)
        order = order_type(quantity=quantity, **kwargs)
        return self.send_order(contract, order)

    def order_target_quantity(self, contract, order_type, target, **kwargs):
        # Place an order to adjust a position to a target number of shares. If
        # the position doesn't already exist, this is equivalent to placing a new
        # order. If the position does exist, this is equivalent to placing an
        # order for the difference between the target number of shares and the
        # current number of shares.
        quantity = self._calculate_order_target_quantity(contract, target)
        order = order_type(
            action=SELL if quantity < 0 else BUY, quantity=abs(quantity), **kwargs
        )
        return self.send_order(contract, order)

    def _calculate_order_target_quantity(self, contract, target):
        positions = self.get_positions()

        if contract.symbol in positions.keys():
            current_position = positions[contract.symbol]["position"]
            target -= current_position

        return int(target)

    def order_percent(self, contract, order_type, percent, **kwargs):
        # Place an order in the specified asset corresponding to the given
        # percent of the current portfolio value.
        quantity = self._calculate_order_percent_quantity(contract, percent)
        order = order_type(quantity=quantity, **kwargs)
        return self.send_order(contract, order)

    def _calculate_order_percent_quantity(self, contract, percent):
        net_liquidation_value = self.get_account_values(key="NetLiquidation")[0]
        value = net_liquidation_value * percent

        return self._calculate_order_value_quantity(contract, value)

    def order_target_value(self, contract, order_type, target, **kwargs):
        # Place an order to adjust a position to a target value. If
        # the position doesn't already exist, this is equivalent to placing a new
        # order. If the position does exist, this is equivalent to placing an
        # order for the difference between the target value and the
        # current value.
        target_quantity = self._calculate_order_value_quantity(contract, target)
        quantity = self._calculate_order_target_quantity(contract, target_quantity)
        order = order_type(
            action=SELL if quantity < 0 else BUY, quantity=abs(quantity), **kwargs
        )
        return self.send_order(contract, order)

    def _calculate_order_value_quantity(self, contract, value):
        last_price = self.get_market_data(
            request_id=DEFAULT_MARKET_DATA_ID, contract=contract, tick_type=4
        )
        multiplier = contract.multiplier if contract.multiplier != "" else 1
        return int(value / (last_price * multiplier))

    def order_target_percent(self, contract, order_type, target, **kwargs):
        # Place an order to adjust a position to a target percent of the
        # current portfolio value. If the position doesn't already exist, this is
        # equivalent to placing a new order. If the position does exist, this is
        # equivalent to placing an order for the difference between the target
        # percent and the current percent.
        quantity = self._calculate_order_target_percent_quantity(contract, target)
        order = order_type(
            action=SELL if quantity < 0 else BUY, quantity=abs(quantity), **kwargs
        )
        return self.send_order(contract, order)

    def _calculate_order_target_percent_quantity(self, contract, target):
        target_quantity = self._calculate_order_percent_quantity(contract, target)
        return self._calculate_order_target_quantity(contract, target_quantity)

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
