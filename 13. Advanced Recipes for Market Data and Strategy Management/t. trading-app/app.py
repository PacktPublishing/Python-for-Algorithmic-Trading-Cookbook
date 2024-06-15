import threading
import time
import empyrical as ep

import sqlite3

from wrapper import IBWrapper
from client import IBClient
from utils import (
    CREATE_BID_ASK_DATA,
    CREATE_ORDER_STATUS,
    CREATE_OPEN_ORDERS,
    CREATE_TRADES,
    CREATE_END_OF_DAY,
    END_OF_DAY_FIELDS,
)


class IBApp(IBWrapper, IBClient):
    def __init__(self, ip, port, client_id, account, interval=5, **kwargs):
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
        time.sleep(5)
        threading.Thread(
            target=self.watch_cvar,
            args=(kwargs["cvar_threshold"], interval),
            daemon=True,
        ).start()

    @property
    def connection(self):
        return sqlite3.connect("strategy_1.sqlite", isolation_level=None)

    def create_table(self):
        cursor = self.connection.cursor()
        cursor.execute(CREATE_BID_ASK_DATA)
        cursor.execute(CREATE_ORDER_STATUS)
        cursor.execute(CREATE_OPEN_ORDERS)
        cursor.execute(CREATE_TRADES)
        cursor.execute(CREATE_END_OF_DAY)

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
        return ep.cum_returns(self.portfolio_returns, 1)

    @property
    def max_drawdown(self):
        return ep.max_drawdown(self.portfolio_returns)

    @property
    def volatility(self):
        return self.portfolio_returns.std(ddof=1)

    @property
    def omega_ratio(self):
        return ep.omega_ratio(self.portfolio_returns, annualization=1)

    @property
    def sharpe_ratio(self):
        return self.portfolio_returns.mean() / self.portfolio_returns.std(ddof=1)

    @property
    def cvar(self):
        net_liquidation = self.get_account_values("NetLiquidation")[0]
        cvar_ = ep.conditional_value_at_risk(self.portfolio_returns)
        return (cvar_, cvar_ * net_liquidation)

    def watch_cvar(self, threshold, interval):
        print("Watching CVaR in 60 seconds...")
        time.sleep(60)
        while True:
            cvar = self.cvar[1]
            if cvar < threshold:
                print(f"Portfolio CVaR ({cvar}) crossed threshold ({threshold})")
                pass
            time.sleep(interval)

    def store_end_of_day(self):
        account_values = self.get_account_values()
        values = {k: v[0] for k, v in account_values.items() if k in END_OF_DAY_FIELDS}
        cursor = self.connection.cursor()
        query = """
INSERT INTO end_of_day (
    account_code,
    available_funds,
    buying_power,
    cash_balance,
    cushion,
    equity_with_loan_value,
    excess_liquidity,
    gross_position_value,
    init_margin_req,
    maint_margin_req,
    money_market_fund_value,
    net_liquidation,
    realized_pnl,
    reg_t_equity,
    reg_t_margin,
    sma,
    unrealized_pnl
) VALUES (
    :AccountCode,
    :AvailableFunds,
    :BuyingPower,
    :CashBalance,
    :Cushion,
    :EquityWithLoanValue,
    :ExcessLiquidity,
    :GrossPositionValue,
    :InitMarginReq,
    :MaintMarginReq,
    :MoneyMarketFundValue,
    :NetLiquidation,
    :RealizedPnL,
    :RegTEquity,
    :RegTMargin,
    :SMA,
    :UnrealizedPnL
)"""
        cursor.execute(query, values)


if __name__ == "__main__":
    app = IBApp(
        "127.0.0.1",
        7497,
        client_id=12,
        account="DU7129120",
        interval=10,
        cvar_threshold=-2000,
    )

    app.store_end_of_day()

    app.disconnect()
