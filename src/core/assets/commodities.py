from core.assets.base import Asset
from core.timeseries import Timeserie


class Commodity(Asset):
    """A physical commodity (oil, gold, corn, ...), tracked by its spot price history."""

    def __init__(self, name: str, spot_prices: Timeserie) -> None:
        super().__init__(name)
        self.spot_prices = spot_prices

    @property
    def spot_price(self) -> float:
        return self.spot_prices.last_price
