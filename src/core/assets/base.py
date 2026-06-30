from abc import ABC


class Asset(ABC):
    """
    Root abstraction for anything that can be held, priced, or referenced
    as the underlying of a derivative (a stock, a commodity, a future, ...).
    """

    def __init__(self, name: str = "default_asset") -> None:
        self.name = name

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name!r})"

    def __eq__(self, other: object) -> bool:
        # Two assets are considered the same economic asset if they share
        # type and name. This matters a lot once we start matching
        # exposures to the right hedging instrument by asset identity.
        return (
            isinstance(other, Asset)
            and type(self) is type(other)
            and self.name == other.name
        )

    def __hash__(self) -> int:
        return hash((type(self).__name__, self.name))
