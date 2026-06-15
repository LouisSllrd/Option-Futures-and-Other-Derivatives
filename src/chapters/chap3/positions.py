from chapters.chap3.futures import Asset, Future


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


class FuturePosition:
    def __init__(self, quantity: int, future: Future, is_long: bool) -> None:
        self.quantity = quantity
        self.future = future
        self.is_long = is_long

    def pnl(self, closing_price: float) -> float:
        price_diff = closing_price - self.future.contract_price
        direction = 1 if self.is_long else -1
        return direction * price_diff * self.quantity * self.future.contract_size


class Portfolio:
    def __init__(self, positions: list[Position]) -> None:
        self.positions = positions
        self.hedging_positions: list[FuturePosition] = []

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
