from core.assets.derivatives.futures import Future
from core.positions import Exposition, FuturePosition, Position


class Portfolio:
    def __init__(
        self,
        positions: list[Position] = [],
        hedging_positions: list[FuturePosition] = [],
    ) -> None:
        self.positions = positions
        self.hedging_positions = hedging_positions

    def short_hedge(self, exposition: Exposition, future: Future) -> FuturePosition:
        n_contracts = round(abs(exposition.sensitivity) / future.contract_size)

        hedge = FuturePosition(
            quantity=n_contracts,
            future=future,
            is_long=False,
        )
        return hedge

    def long_hedge(self, exposition: Exposition, future: Future) -> FuturePosition:
        n_contracts = round(abs(exposition.sensitivity) / future.contract_size)

        hedge = FuturePosition(
            quantity=n_contracts,
            future=future,
            is_long=True,
        )
        return hedge

    def hedge(self) -> None:
        for position in self.positions:
            for expo in position.expositions:
                if expo.sensitivity > 0:
                    hedge = self.short_hedge(exposition=expo, future=Future())
                else:
                    hedge = self.long_hedge(exposition=expo, future=Future())
                self.hedging_positions.append(hedge)
