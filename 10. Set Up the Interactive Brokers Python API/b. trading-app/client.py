from ibapi.client import EClient


class IBClient(EClient):
    def __init__(self, wrapper):
        EClient.__init__(self, wrapper)
