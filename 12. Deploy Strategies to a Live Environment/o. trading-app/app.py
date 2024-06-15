import os
import sqlite3
import threading
import time

import empyrical as ep
import exchange_calendars as xcals
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from zipline.data import bundles
from zipline.data.bundles.core import load
from zipline.pipeline import Pipeline
from zipline.pipeline.data import USEquityPricing
from zipline.pipeline.engine import SimplePipelineEngine
from zipline.pipeline.factors import CustomFactor, Returns
from zipline.pipeline.loaders import USEquityPricingLoader
from zipline.utils.run_algo import load_extensions

from client import IBClient
from contract import stock
from order import market
from wrapper import IBWrapper

load_dotenv()


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


class MomentumFactor(CustomFactor):
    inputs = [USEquityPricing.close, Returns(window_length=126)]
    window_length = 252

    def compute(self, today, assets, out, prices, returns):
        out[:] = (
            (prices[-21] - prices[-252]) / prices[-252]
            - (prices[-1] - prices[-21]) / prices[-21]
        ) / np.nanstd(returns, axis=0)


def make_pipeline():
    momentum = MomentumFactor()
    return Pipeline(
        columns={
            "factor": momentum,
            "longs": momentum.top(top_n),
            "shorts": momentum.bottom(top_n),
            "rank": momentum.rank(ascending=False),
        },
    )


if __name__ == "__main__":
    app = IBApp("127.0.0.1", 7497, client_id=11, account="DU7129120")

    top_n = 10
    xnys = xcals.get_calendar("XNYS")
    today = pd.Timestamp.today().strftime("%Y-%m-%d")
    start_date = xnys.session_offset(today, count=-252).strftime("%Y-%m-%d")

    load_extensions(True, [], False, os.environ)
    bundles.ingest("quotemedia")
    bundle_data = load("quotemedia", os.environ, None)

    pipeline_loader = USEquityPricingLoader(
        bundle_data.equity_daily_bar_reader,
        bundle_data.adjustment_reader,
        fx_reader=None,
    )

    engine = SimplePipelineEngine(
        get_loader=lambda col: pipeline_loader, asset_finder=bundle_data.asset_finder
    )

    results = engine.run_pipeline(make_pipeline(), start_date, today)

    results.dropna(subset="factor", inplace=True)
    results.index.names = ["date", "symbol"]
    results.sort_values(by=["date", "factor"], inplace=True)

    longs = results.xs("2023-12-15", level=0).query("longs == True")
    shorts = results.xs("2023-12-15", level=0).query("shorts == True")

    weight = 1 / top_n / 2

    for row in pd.concat([longs, shorts]).itertuples():
        side = 1 if row.longs else -1
        symbol = row.Index.symbol

        contract = stock(symbol, "SMART", "USD")
        app.order_target_percent(contract, market, side * weight)

    time.sleep(30)
    app.disconnect()
