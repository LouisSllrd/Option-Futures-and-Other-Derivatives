import pandas as pd

from core.assets.base import Asset


class Future(Asset):
    def __init__(
        self,
        name: str,
        underlying: Asset,
        contract_price: float,
        maturity: pd.Timestamp,
        contract_size: int = 1000,
    ) -> None:
        super().__init__(name)
        self.underlying = underlying
        self.contract_price = contract_price
        self.maturity = maturity
        self.contract_size = contract_size
