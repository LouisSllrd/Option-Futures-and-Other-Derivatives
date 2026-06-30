from core.assets.base import Asset
from core.timeseries import Timeserie


class Stock(Asset):
    """An equity, tracked by its price history."""

    def __init__(self, name: str, prices: Timeserie) -> None:
        super().__init__(name)
        self.prices = prices

    @property
    def spot_price(self) -> float:
        return self.prices.last_price
