from core.assets.base import Asset
from core.timeseries import Timeserie


class Commodity(Asset):
    def __init__(self, name: str, spot_prices: Timeserie) -> None:
        super().__init__(name)
        self.spot_prices = spot_prices
