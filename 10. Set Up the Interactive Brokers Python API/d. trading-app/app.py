import threading
import time

from wrapper import IBWrapper
from client import IBClient
from contract import stock, future, option


class IBApp(IBWrapper, IBClient):
    def __init__(self, ip, port, client_id):
        IBWrapper.__init__(self)
        IBClient.__init__(self, wrapper=self)

        self.connect(ip, port, client_id)

        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
        time.sleep(2)


if __name__ == "__main__":
    app = IBApp("127.0.0.1", 7497, client_id=10)

    aapl = stock("AAPL", "SMART", "USD")
    gbl = future("GBL", "EUREX", "202403")
    pltr = option("PLTR", "BOX", "20240315", 20, "C")

    data = app.get_historical_data(
        request_id=99, contract=aapl, duration="2 D", bar_size="30 secs"
    )

    time.sleep(30)
    app.disconnect()
