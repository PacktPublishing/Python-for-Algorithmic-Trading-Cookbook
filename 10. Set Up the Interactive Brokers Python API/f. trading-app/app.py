import threading
import time

from wrapper import IBWrapper
from client import IBClient
from contract import future


class IBApp(IBWrapper, IBClient):
    def __init__(self, ip, port, client_id):
        IBWrapper.__init__(self)
        IBClient.__init__(self, wrapper=self)

        self.connect(ip, port, client_id)

        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
        time.sleep(2)

    def get_streaming_data(self, request_id, contract):
        self.reqMktData(
            reqId=request_id,
            contract=contract,
            genericTickList="",
            snapshot=False,
            regulatorySnapshot=False,
            mktDataOptions=[],
        )

        while True:
            if request_id in self.market_data:
                yield self.market_data[request_id]
            time.sleep(1)


if __name__ == "__main__":
    app = IBApp("127.0.0.1", 7497, client_id=10)

    eur = future("EUR", "CME", "202312")
    for tick in app.get_streaming_data(99, eur):
        print(tick)

    time.sleep(30)
    app.disconnect()
