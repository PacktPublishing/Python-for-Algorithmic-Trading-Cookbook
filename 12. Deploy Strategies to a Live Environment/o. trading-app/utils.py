import pandas as pd
from dataclasses import dataclass, field


TRADE_BAR_PROPERTIES = ["time", "open", "high", "low", "close", "volume"]

DEFAULT_MARKET_DATA_ID = 55


@dataclass
class Tick:
    time: int
    bid_price: float
    ask_price: float
    bid_size: int
    ask_size: int
    timestamp_: pd.Timestamp = field(init=False)

    def __post_init__(self):
        self.timestamp_ = pd.to_datetime(self.time, unit="s")
        self.bid_price = float(self.bid_price)
        self.ask_price = float(self.ask_price)
        self.bid_size = int(self.bid_size)
        self.ask_size = int(self.ask_size)
