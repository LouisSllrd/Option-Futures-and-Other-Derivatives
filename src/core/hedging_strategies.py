from abc import ABC, abstractmethod

import pandas as pd

from core.assets.base import Asset
from core.assets.derivatives.basis import CrossHedge
from core.assets.derivatives.futures import Future, StockIndexFuture
from core.portfolios import Portfolio
from core.positions import Exposition, FuturePosition, Position
from db.connection import DatabaseConnection


class HedgingStrategy(ABC):
    """
    A strategy turns a portfolio's *residual* exposures (i.e. net of any
    hedging positions already in place) into new hedging positions.
    """

    @abstractmethod
    def build_hedges(self, residual_expositions: list[Exposition]) -> list[Position]:
        """Given residual exposures to neutralize, return the hedging positions to add."""

    def apply_to(
        self, portfolio: Portfolio, targeted_positions: list[Position] | None = None
    ) -> None:
        positions = (
            targeted_positions
            if targeted_positions is not None
            else portfolio.positions
        )
        residuals = portfolio.residual_expositions(positions)
        new_hedges = self.build_hedges(residuals)
        portfolio.hedging_positions.extend(new_hedges)


class FutureHedging(HedgingStrategy):
    """
    Default 1-for-1 future hedging (Hull section 3.1/3.2): for each residual
    exposure, picks the future whose underlying matches the exposed asset
    directly, taken from the database, and sizes a fully offsetting
    futures position.

    No `Future` instance needs to be supplied up front: the right contract
    is looked up per-exposure based on the asset it is exposed to. This is
    what lets a single FutureHedging instance correctly hedge a portfolio
    that mixes, say, an oil exposure and a gold exposure.
    """

    def __init__(
        self, database: DatabaseConnection | None = None, as_of: pd.Timestamp = None
    ) -> None:
        self.database = database or DatabaseConnection()
        self.as_of = as_of

    def _find_future_for(self, asset: Asset) -> Future:
        future = self.database.find_future_for_underlying(asset)
        if future is None:
            raise LookupError(
                f"No future found in the database whose underlying matches {asset!r}. "
                "Consider CrossHedging if you intend to hedge with a related instrument."
            )
        return future

    def _contracts_needed(self, exposition: Exposition, future: Future) -> int:
        return round(abs(exposition.sensitivity) / future.contract_size)

    def build_hedges(self, residual_expositions: list[Exposition]) -> list[Position]:
        hedges: list[Position] = []
        for expo in residual_expositions:
            if expo.sensitivity == 0:
                continue

            future = self._find_future_for(expo.sensitive_asset)
            quantity = self._contracts_needed(expo, future)
            if quantity == 0:
                continue

            # A positive exposition (gains when the asset rises) is offset
            # by going short the future; a negative exposition is offset
            # by going long.
            hedges.append(
                FuturePosition(
                    risk_free_rate=0.0,
                    date=self.as_of or future.maturity,
                    quantity=quantity,
                    future=future,
                    is_long=expo.sensitivity < 0,
                )
            )
        return hedges


class CrossHedgeStrategy(HedgingStrategy):
    """
    Cross hedging (Hull section 3.4): used when no future trades directly
    on the exposed asset, so a *related* future is used instead and the
    hedge ratio is no longer 1.0 but the minimum-variance hedge ratio h*.

    The caller supplies the substitute future explicitly (by asset) since,
    unlike FutureHedging, there is no unambiguous "right" contract to
    discover automatically — the choice of a correlated proxy is a modeling
    decision, not a lookup.
    """

    def __init__(
        self, future_by_asset: dict[Asset, Future], tailed: bool = False
    ) -> None:
        self.future_by_asset = future_by_asset
        self.tailed = tailed

    def build_hedges(self, residual_expositions: list[Exposition]) -> list[Position]:
        hedges: list[Position] = []
        for expo in residual_expositions:
            future = self.future_by_asset.get(expo.sensitive_asset)
            if future is None or expo.sensitivity == 0:
                continue

            hedged_prices = self._price_history_of(expo.sensitive_asset)
            cross_hedge = CrossHedge(future=future, hedged_asset_prices=hedged_prices)
            quantity = cross_hedge.optimal_contracts(
                abs(expo.sensitivity), tailed=self.tailed
            )
            if quantity == 0:
                continue

            hedges.append(
                FuturePosition(
                    risk_free_rate=0.0,
                    date=future.maturity,
                    quantity=quantity,
                    future=future,
                    is_long=expo.sensitivity < 0,
                )
            )
        return hedges

    @staticmethod
    def _price_history_of(asset: Asset):
        if hasattr(asset, "spot_prices"):
            return asset.spot_prices
        if hasattr(asset, "prices"):
            return asset.prices
        raise AttributeError(
            f"Asset {asset!r} carries no price history to cross-hedge against."
        )


class BetaHedging(HedgingStrategy):
    """
    Hedging (or beta-tilting) an equity portfolio with stock index futures
    (Hull section 3.5): N* = beta * VA / VF, optionally targeting a beta
    other than zero via `target_beta`.

    Unlike FutureHedging/CrossHedgeStrategy, this strategy does not act on
    per-asset Expositions: it acts directly on the *portfolio value* and a
    single beta number, because the whole point is to hedge a diversified
    basket rather than asset-by-asset exposures.
    """

    def __init__(
        self, index_future: StockIndexFuture, beta: float, target_beta: float = 0.0
    ) -> None:
        self.index_future = index_future
        self.beta = beta
        self.target_beta = target_beta

    def hedge_portfolio_value(self, portfolio_value: float) -> FuturePosition:
        beta_gap = self.beta - self.target_beta
        contracts = round(
            abs(beta_gap) * portfolio_value / self.index_future.contract_value
        )
        return FuturePosition(
            risk_free_rate=0.0,
            date=self.index_future.maturity,
            quantity=contracts,
            future=self.index_future,
            # beta_gap > 0 means the portfolio is more sensitive to the
            # market than the target, so it is short the index to reduce it.
            is_long=beta_gap < 0,
        )

    def build_hedges(self, residual_expositions: list[Exposition]) -> list[Position]:
        # BetaHedging is invoked directly via hedge_portfolio_value(); it
        # does not consume per-asset residual expositions like the other
        # strategies, so Portfolio.hedge() should call it through a
        # dedicated entry point rather than apply_to(). See Portfolio.hedge_beta().
        raise NotImplementedError(
            "BetaHedging is applied via Portfolio.hedge_beta(), not the generic apply_to()."
        )
