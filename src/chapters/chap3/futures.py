from abc import ABC

import pandas as pd


class Asset(ABC):
    def __init__(self, name: str = "default_asset") -> None:
        self.name = name


class Commodity(Asset):
    def __init__(self, name: str, spot_price: float) -> None:
        super().__init__(name)
        self.spot_price = spot_price


class Future:
    def __init__(
        self,
        underlying: Asset,
        contract_price: float,
        maturity: pd.Timestamp,
        contract_size: int = 1000,
    ) -> None:
        self.underlying = underlying
        self.contract_price = contract_price
        self.maturity = maturity
        self.contract_size = contract_size
