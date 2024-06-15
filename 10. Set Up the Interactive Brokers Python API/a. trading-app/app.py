import threading
import time

from wrapper import IBWrapper
from client import IBClient


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

    time.sleep(30)
    app.disconnect()
