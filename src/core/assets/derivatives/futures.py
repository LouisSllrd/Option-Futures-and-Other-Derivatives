import pandas as pd

from core.assets.base import Asset


class Future(Asset):
    """
    A futures contract on `underlying`, at `contract_price`, maturing on
    `maturity`, covering `contract_size` units of the underlying per contract.
    """

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

    @property
    def contract_value(self) -> float:
        """VF in Hull's notation: the dollar value of a single futures contract."""
        return self.contract_price * self.contract_size

    def basis(self, spot_price: float | None = None) -> float:
        """
        Basis = spot price of the asset to be hedged - futures price.

        If the hedged asset is exactly the future's own underlying,
        `spot_price` can be omitted and the underlying's current spot
        price is used. When cross-hedging (the hedged asset differs from
        the future's underlying), the caller must pass the spot price of
        the *actual* hedged asset explicitly.
        """
        reference_spot = (
            spot_price if spot_price is not None else self.underlying.spot_price
        )
        return reference_spot - self.contract_price

    def matches(self, asset: Asset) -> bool:
        """True if this future's underlying is exactly the given asset (no cross-hedge)."""
        return self.underlying == asset

    def days_to_maturity(self, as_of: pd.Timestamp) -> int:
        return (self.maturity - as_of).days


class StockIndexFuture(Future):
    """
    A futures contract on a stock index (e.g. S&P 500 mini future).

    Behaves like a regular Future, but is the natural hedging instrument
    for an equity *portfolio* characterized by a beta rather than a single
    underlying asset. The underlying here is conceptually "the index", we
    still model it as an Asset (e.g. a Commodity-like price series could be
    reused, or a dedicated Index asset) so that contract_value / basis still
    work unmodified.
    """

    def __init__(
        self,
        name: str,
        underlying: Asset,
        contract_price: float,
        maturity: pd.Timestamp,
        contract_size: int,
        dividend_yield: float = 0.0,
    ) -> None:
        super().__init__(name, underlying, contract_price, maturity, contract_size)
        self.dividend_yield = dividend_yield
