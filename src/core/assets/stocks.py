from core.assets.base import Asset
from core.timeseries import Timeserie


class Stock(Asset):
    def __init__(self, name: str, prices: Timeserie) -> None:
        super().__init__(name)
        self.prices = prices
