import threading
import time
import empyrical as ep

import sqlite3

from wrapper import IBWrapper
from client import IBClient
from contract import stock, future, option
from order import limit, BUY


class IBApp(IBWrapper, IBClient):
    def __init__(self, ip, port, client_id, account, interval=5):
        IBWrapper.__init__(self)
        IBClient.__init__(self, wrapper=self)
        self.account = account
        self.create_table()

        self.connect(ip, port, client_id)

        threading.Thread(target=self.run, daemon=True).start()
        time.sleep(5)
        threading.Thread(
            target=self.get_streaming_returns,
            args=(99, interval, "unrealized_pnl"),
            daemon=True,
        ).start()

    @property
    def connection(self):
        return sqlite3.connect("tick_data.sqlite", isolation_level=None)

    def create_table(self):
        cursor = self.connection.cursor()
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS bid_ask_data (timestamp datetime, symbol string, bid_price real, ask_price real, bid_size integer, ask_size integer)"
        )

    def stream_to_sqlite(self, request_id, contract, run_for_in_seconds=23400):
        cursor = self.connection.cursor()
        end_time = time.time() + run_for_in_seconds + 10
        for tick in app.get_streaming_data(request_id, contract):
            query = "INSERT INTO bid_ask_data (timestamp, symbol, bid_price, ask_price, bid_size, ask_size) VALUES (?, ?, ?, ?, ?, ?)"
            values = (
                tick.timestamp_.strftime("%Y-%m-%d %H:%M:%S"),
                contract.symbol,
                tick.bid_price,
                tick.ask_price,
                tick.bid_size,
                tick.ask_size,
            )
            cursor.execute(query, values)
            if time.time() >= end_time:
                break

        self.stop_streaming_data(request_id)

    @property
    def cumulative_returns(self):
        return ep.cum_returns(self.account_returns, 1)

    @property
    def max_drawdown(self):
        return ep.max_drawdown(self.account_returns)

    @property
    def volatility(self):
        return self.account_returns.std(ddof=1)

    @property
    def omega_ratio(self):
        return ep.omega_ratio(self.account_returns, annualization=1)

    @property
    def sharpe_ratio(self):
        return self.account_returns.mean() / self.account_returns.std(ddof=1)

    @property
    def cvar(self):
        net_liquidation = self.get_account_values("NetLiquidation")[0]
        cvar_ = ep.conditional_value_at_risk(self.account_returns)
        return (cvar_, cvar_ * net_liquidation)


if __name__ == "__main__":
    app = IBApp("127.0.0.1", 7497, client_id=11, account="DU7129120")

    time.sleep(200)

    print(app.cumulative_returns)
    print(app.max_drawdown)
    print(app.volatility)
    print(app.omega_ratio)
    print(app.sharpe_ratio)
    print(app.cvar)

    # request_id, warm_up=5, interval=60, pnl_type="unrealized_pnl"
    # for snapshot in app.stream_portfolio_returns(request_id=99, window=5, interval=5, pnl_type="unrealized_pnl"):
    #     print(snapshot)

    app.disconnect()
