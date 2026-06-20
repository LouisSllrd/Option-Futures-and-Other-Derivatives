from asyncio import Future

import numpy as np
import pandas as pd

from core.assets.base import Asset


class Exposition:
    def __init__(self, sensitive_asset: Asset, sensitivity: float) -> None:
        self.sensitive_asset = sensitive_asset
        self.sensitivity = sensitivity


class Position:
    def __init__(
        self,
        quantity: float,
        asset: Asset,
        is_long: bool,
        expositions: list[Exposition] | None = None,
    ) -> None:
        self.quantity = quantity
        self.asset = asset
        self.is_long = is_long
        self.expositions = expositions or []


class FuturePosition(Position):
    def __init__(
        self,
        risk_free_rate: float,
        date: pd.Timestamp,
        quantity: float,
        future: Future,
        is_long: bool,
    ) -> None:
        self.date = date
        direction = 1 if is_long else -1
        sensitivity = (
            direction
            * quantity
            * np.exp(risk_free_rate * (future.maturity - date).days / 365)
        )
        super().__init__(
            quantity=quantity,
            asset=future,
            is_long=is_long,
            expositions=[
                Exposition(sensitive_asset=future.underlying, sensitivity=sensitivity)
            ],
        )

    def pnl(self, closing_price: float) -> float:
        price_diff = closing_price - self.asset.contract_price
        direction = 1 if self.is_long else -1
        return direction * price_diff * self.quantity * self.asset.contract_size
