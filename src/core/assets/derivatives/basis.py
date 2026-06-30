from dataclasses import dataclass

from core.assets.base import Asset
from core.assets.derivatives.futures import Future
from core.timeseries import Timeserie


@dataclass(frozen=True)
class Basis:
    """
    Snapshot of a basis at a point in time: Basis = S - F.

    Kept as its own small value object (rather than a bare float) so that
    callers always know which spot/futures pair produced it, and so we can
    qualify "strengthening" / "weakening" without recomputing inputs.
    """

    spot_price: float
    futures_price: float

    @property
    def value(self) -> float:
        return self.spot_price - self.futures_price

    def change_since(self, earlier: "Basis") -> float:
        """Positive => the basis has strengthened since `earlier`; negative => weakened."""
        return self.value - earlier.value


class BasisRiskCalculator:
    """
    Computes the effective hedged price (Hull eq. in section 3.3) and
    decomposes basis risk into its "pure" and "cross-hedge" components.

    Effective price for a hedger who is short futures and sells the asset
    at t2 (or long futures and buys the asset at t2):
        effective_price = F1 + b2
    where F1 is the futures price when the hedge was initiated and b2 is
    the basis at the time the hedge is closed out. This holds for both the
    short-hedge-then-sell and long-hedge-then-buy cases (Hull is explicit
    that the formula is identical in both).
    """

    def __init__(self, future: Future, hedged_asset: Asset) -> None:
        self.future = future
        self.hedged_asset = hedged_asset

    @property
    def is_cross_hedge(self) -> bool:
        return not self.future.matches(self.hedged_asset)

    def basis_at(self, spot_price: float, futures_price: float) -> Basis:
        return Basis(spot_price=spot_price, futures_price=futures_price)

    def effective_price(
        self,
        initial_futures_price: float,
        final_basis: Basis,
    ) -> float:
        """effective_price = F1 + b2."""
        return initial_futures_price + final_basis.value

    def decompose_cross_hedge_basis(
        self,
        hedged_asset_spot_t2: float,
        underlying_spot_t2: float,
        futures_price_t2: float,
    ) -> tuple[float, float]:
        """
        Splits the basis at t2 into:
          - the "pure" basis that would exist if the hedged asset and the
            future's underlying were the same: (S*_2 - F2)
          - the cross-hedge spread between the two assets: (S2 - S*_2)

        Returns (pure_basis, cross_hedge_spread); their sum is the total
        basis S2 - F2 used in `effective_price`.
        """
        pure_basis = underlying_spot_t2 - futures_price_t2
        cross_hedge_spread = hedged_asset_spot_t2 - underlying_spot_t2
        return pure_basis, cross_hedge_spread


class CrossHedge:
    """
    Minimum-variance hedge ratio and optimal contract count for cross
    hedging (Hull section 3.4), estimated from historical (Delta S, Delta F)
    observations carried by the hedged asset's and the future's Timeseries.
    """

    def __init__(self, future: Future, hedged_asset_prices: Timeserie) -> None:
        self.future = future
        self.hedged_asset_prices = hedged_asset_prices

    def _futures_price_history(self) -> Timeserie:
        # The future itself does not carry a price history in this model
        # (only its current contract_price); for hedge-ratio estimation we
        # reuse the underlying's history as a proxy for historical futures
        # price changes, which is the standard simplifying assumption when
        # a dedicated futures price series isn't tracked separately.
        underlying = self.future.underlying
        if hasattr(underlying, "spot_prices"):
            return underlying.spot_prices
        if hasattr(underlying, "prices"):
            return underlying.prices
        raise AttributeError(
            f"Underlying asset {underlying!r} exposes no price history to use as a futures proxy."
        )

    def hedge_ratio(self, tailed: bool = False) -> float:
        """
        h* = rho * (sigma_S / sigma_F)   (Hull eq. 3.1, or its tailed
        percentage-change variant when `tailed=True`, eq. used for daily
        settlement futures).
        """
        futures_prices = self._futures_price_history()
        rho = Timeserie.correlation(
            self.hedged_asset_prices, futures_prices, pct=tailed
        )
        sigma_s = self.hedged_asset_prices.historical_volatility(pct=tailed)
        sigma_f = futures_prices.historical_volatility(pct=tailed)
        return rho * (sigma_s / sigma_f)

    def hedge_effectiveness(self, tailed: bool = False) -> float:
        """R^2 of the regression, i.e. rho^2: the proportion of variance eliminated."""
        futures_prices = self._futures_price_history()
        rho = Timeserie.correlation(
            self.hedged_asset_prices, futures_prices, pct=tailed
        )
        return rho**2

    def optimal_contracts(self, exposure_units: float, tailed: bool = False) -> int:
        """N* = h* * QA / QF (Hull eq. 3.2)."""
        h_star = self.hedge_ratio(tailed=tailed)
        return round(h_star * exposure_units / self.future.contract_size)
