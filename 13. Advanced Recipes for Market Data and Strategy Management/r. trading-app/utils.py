import pandas as pd
from dataclasses import dataclass, field


TRADE_BAR_PROPERTIES = ["time", "open", "high", "low", "close", "volume"]

DEFAULT_MARKET_DATA_ID = 55
DEFAULT_CONTRACT_ID = 44

CREATE_BID_ASK_DATA = """
CREATE TABLE IF NOT EXISTS bid_ask_data
  (
     timestamp DATETIME,
     symbol STRING,
     bid_price REAL,
     ask_price REAL,
     bid_size INTEGER,
     ask_size INTEGER
  )"""


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
