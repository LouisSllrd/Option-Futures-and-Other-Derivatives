from abc import ABC, abstractmethod

import numpy as np
import pandas as pd

from core.assets.base import Asset
from core.assets.derivatives.futures import Future


class Exposition:
    """
    A position's sensitivity to a given asset's price.

    `sensitivity` is expressed in "units of the asset" (e.g. barrels of
    oil, shares of stock, $ of index notional once converted), with sign:
    positive => the position gains when the asset's price rises (long-like
    exposure that needs a short hedge), negative => the opposite.
    """

    def __init__(self, sensitive_asset: Asset, sensitivity: float) -> None:
        self.sensitive_asset = sensitive_asset
        self.sensitivity = sensitivity

    def __repr__(self) -> str:
        return (
            f"Exposition({self.sensitive_asset!r}, sensitivity={self.sensitivity:.4f})"
        )


class Position(ABC):
    """
    Base class for anything held in a portfolio.

    `exposition` is intentionally a property, not a stored attribute:
    a position's risk exposure can depend on time-varying inputs (time to
    maturity, discounting, spot levels, ...), so it must be recomputed on
    demand rather than frozen at construction time.
    """

    def __init__(
        self,
        risk_free_rate: float,
        date: pd.Timestamp,
        quantity: float,
        asset: Asset,
        is_long: bool,
    ) -> None:
        self.risk_free_rate = risk_free_rate
        self.date = date
        self.quantity = quantity
        self.asset = asset
        self.is_long = is_long

    @property
    def direction(self) -> int:
        return 1 if self.is_long else -1

    @property
    @abstractmethod
    def expositions(self) -> list[Exposition]:
        """All elementary exposures carried by this position."""

    def exposition_to(self, asset: Asset) -> float:
        """Net sensitivity of this position to a specific asset (0.0 if none)."""
        return sum(
            e.sensitivity for e in self.expositions if e.sensitive_asset == asset
        )


class SpotPosition(Position):
    """
    A plain holding of an asset (e.g. owning the physical commodity, or
    shares of a stock) with no leverage or discounting effects: its
    exposure to its own asset is simply its (signed) quantity.
    """

    @property
    def expositions(self) -> list[Exposition]:
        return [
            Exposition(
                sensitive_asset=self.asset, sensitivity=self.direction * self.quantity
            )
        ]


class FuturePosition(Position):
    """
    A position in a futures contract.

    The exposure carried by a futures position is to its *underlying*
    asset, not to the future itself, and its magnitude is discounted by
    the time remaining to maturity (the classic continuously-compounded
    forward-value adjustment), so it is computed dynamically from
    `self.date` rather than frozen at construction time.
    """

    def __init__(
        self,
        risk_free_rate: float,
        date: pd.Timestamp,
        quantity: float,
        future: Future,
        is_long: bool,
    ) -> None:
        super().__init__(
            risk_free_rate=risk_free_rate,
            date=date,
            quantity=quantity,
            asset=future,
            is_long=is_long,
        )

    @property
    def future(self) -> Future:
        return self.asset

    @property
    def expositions(self) -> list[Exposition]:
        time_to_maturity_years = self.future.days_to_maturity(self.date) / 365
        discount_factor = np.exp(self.risk_free_rate * time_to_maturity_years)
        # quantity is a number of *contracts*; convert to underlying units
        # (contract_size per contract) so this exposure is directly
        # comparable with — and nettable against — a SpotPosition's
        # exposure to the same underlying asset.
        units_of_underlying = self.quantity * self.future.contract_size
        sensitivity = self.direction * units_of_underlying * discount_factor
        return [
            Exposition(sensitive_asset=self.future.underlying, sensitivity=sensitivity)
        ]

    def pnl(self, closing_price: float) -> float:
        price_diff = closing_price - self.future.contract_price
        return self.direction * price_diff * self.quantity * self.future.contract_size
