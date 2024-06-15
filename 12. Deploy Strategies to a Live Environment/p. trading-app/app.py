import threading
import time
import empyrical as ep

import sqlite3

from wrapper import IBWrapper
from client import IBClient
from contract import option, combo_leg, spread
from order import market, BUY, SELL


class IBApp(IBWrapper, IBClient):
    def __init__(self, ip, port, client_id, account, interval=5):
        IBWrapper.__init__(self)
        IBClient.__init__(self, wrapper=self)
        self.account = account
        self.create_table()

        self.connect(ip, port, client_id)

        threading.Thread(target=self.run, daemon=True).start()
        time.sleep(5)
        # threading.Thread(
        #     target=self.get_streaming_returns,
        #     args=(99, interval, "unrealized_pnl"),
        #     daemon=True
        # ).start()

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

    long_call_contract = option("TSLA", "SMART", "202403", 260, "CALL")
    long_call = app.resolve_contract(long_call_contract)

    long_put_contract = option("TSLA", "SMART", "202404", 260, "PUT")
    long_put = app.resolve_contract(long_put_contract)

    leg_1 = combo_leg(long_call, 1, BUY)
    leg_2 = combo_leg(long_put, 1, BUY)

    long_strangle = spread([leg_1, leg_2])

    order = market(BUY, 1)
    app.send_order(long_strangle, order)

    short_call = app.resolve_contract(option("TSLA", "SMART", "202403", 295, "CALL"))
    long_call = app.resolve_contract(option("TSLA", "SMART", "202403", 305, "CALL"))
    short_put = app.resolve_contract(option("TSLA", "SMART", "202403", 240, "PUT"))
    long_put = app.resolve_contract(option("TSLA", "SMART", "202403", 230, "PUT"))

    leg_1 = combo_leg(short_call, 1, SELL)
    leg_2 = combo_leg(long_call, 1, BUY)
    leg_3 = combo_leg(short_put, 1, SELL)
    leg_4 = combo_leg(long_put, 1, BUY)

    short_iron_condor = spread([leg_1, leg_2, leg_3, leg_4])

    order = market(BUY, 1)
    app.send_order(short_iron_condor, order)

    app.disconnect()
