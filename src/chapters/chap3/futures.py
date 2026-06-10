from abc import ABC

import pandas as pd


class Asset(ABC):
    def __init__(self, name: str) -> None:
        self.name = name


class Future(Asset):
    def __init__(
        self,
        contract_price: float,
        maturity: pd.Timestamp,
        underlying: Asset,
    ) -> None:
        self.contract_price = contract_price
        self.maturity = maturity
        self.underlying = underlying
