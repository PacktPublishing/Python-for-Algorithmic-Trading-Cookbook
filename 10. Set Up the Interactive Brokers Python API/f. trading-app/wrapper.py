import threading
from ibapi.wrapper import EWrapper


class IBWrapper(EWrapper):
    def __init__(self):
        EWrapper.__init__(self)
        self.historical_data = {}
        self.market_data = {}
        self.streaming_data = {}
        self.stream_event = threading.Event()

    def historicalData(self, request_id, bar):
        bar_data = (
            bar.date,
            bar.open,
            bar.high,
            bar.low,
            bar.close,
            bar.volume,
        )
        if request_id not in self.historical_data:
            self.historical_data[request_id] = []
        self.historical_data[request_id].append(bar_data)

    def tickPrice(self, request_id, tick_type, price, attrib):
        if request_id not in self.market_data:
            self.market_data[request_id] = {}
        self.market_data[request_id][tick_type] = float(price)

    def tickByTickBidAsk(
        self,
        request_id,
        time,
        bid_price,
        ask_price,
        bid_size,
        ask_size,
        tick_attrib_last,
    ):
        tick_data = (
            time,
            bid_price,
            ask_price,
            bid_size,
            ask_size,
        )
        self.streaming_data[request_id] = tick_data
        self.stream_event.set()
