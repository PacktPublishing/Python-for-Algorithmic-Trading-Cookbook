import threading
import time

import sqlite3

from wrapper import IBWrapper
from client import IBClient
from contract import stock, future, option
from order import limit, BUY


class IBApp(IBWrapper, IBClient):
    def __init__(self, ip, port, client_id):
        IBWrapper.__init__(self)
        IBClient.__init__(self, wrapper=self)
        self.create_table()

        self.connect(ip, port, client_id)

        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
        time.sleep(2)

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


if __name__ == "__main__":
    app = IBApp("127.0.0.1", 7497, client_id=11)

    aapl = stock("AAPL", "SMART", "USD")

    # send a limit order
    order_1 = limit(BUY, 10, 185.0)
    order_1_id = app.send_order(aapl, order_1)

    time.sleep(3)

    # cancel the order
    app.cancel_order_by_id(order_1_id)

    time.sleep(3)

    # send another limit order
    order_1_id = app.send_order(aapl, order_1)

    time.sleep(3)

    order_2 = limit(BUY, 10, 187.50)
    app.update_order(aapl, order_2, order_1_id)

    time.sleep(3)

    app.cancel_all_orders()

    app.disconnect()
