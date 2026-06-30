from typing import TYPE_CHECKING

from core.assets.base import Asset
from core.positions import Exposition, FuturePosition, Position

if TYPE_CHECKING:
    from core.hedging_strategies import BetaHedging, HedgingStrategy


class Portfolio:
    """
    Holds business positions plus the hedging positions taken against them.

    Hedging positions are kept in a separate list (not mixed into
    `positions`) precisely so that we can compute *residual* exposure —
    what's still unhedged — by netting `positions` against
    `hedging_positions`, which is what makes `.hedge(...)` idempotent
    instead of re-hedging an already-hedged exposure every time it's called.
    """

    def __init__(
        self,
        positions: list[Position] | None = None,
        hedging_positions: list[Position] | None = None,
    ) -> None:
        self.positions: list[Position] = positions if positions is not None else []
        self.hedging_positions: list[Position] = (
            hedging_positions if hedging_positions is not None else []
        )

    def net_exposition_to(
        self, asset: Asset, positions: list[Position] | None = None
    ) -> float:
        """
        Net sensitivity to `asset` across the given positions (defaults to
        `self.positions`) *minus* whatever is already offset by existing
        hedging_positions. This is what should drive any new hedge sizing.
        """
        target_positions = positions if positions is not None else self.positions
        gross = sum(p.exposition_to(asset) for p in target_positions)
        already_hedged = sum(p.exposition_to(asset) for p in self.hedging_positions)
        return gross + already_hedged

    def residual_expositions(
        self, positions: list[Position] | None = None
    ) -> list[Exposition]:
        """
        One Exposition per distinct asset referenced by `positions`,
        already netted against existing hedging_positions. Assets with a
        net residual of 0 are simply omitted.
        """
        target_positions = positions if positions is not None else self.positions

        assets_seen: dict[Asset, None] = {}
        for position in target_positions:
            for expo in position.expositions:
                assets_seen.setdefault(expo.sensitive_asset, None)

        residuals = []
        for asset in assets_seen:
            net = self.net_exposition_to(asset, target_positions)
            if net != 0:
                residuals.append(Exposition(sensitive_asset=asset, sensitivity=net))
        return residuals

    def hedge(
        self,
        strategy: "HedgingStrategy",
        targeted_positions: list[Position] | None = None,
    ) -> None:
        """Apply a HedgingStrategy *instance* against (a subset of) positions."""
        strategy.apply_to(self, targeted_positions)

    def hedge_beta(self, strategy: "BetaHedging") -> FuturePosition:
        """
        Dedicated entry point for BetaHedging, which hedges the portfolio's
        *value* against an index rather than netting per-asset exposures.
        The resulting position is appended to hedging_positions and returned.
        """
        hedge_position = strategy.hedge_portfolio_value(self.value)
        self.hedging_positions.append(hedge_position)
        return hedge_position

    @property
    def value(self) -> float:
        """Current mark-to-market value of the (non-hedging) positions, VA in Hull's notation."""
        total = 0.0
        for position in self.positions:
            price = getattr(position.asset, "spot_price", None)
            if price is None:
                continue
            total += position.direction * position.quantity * price
        return total
