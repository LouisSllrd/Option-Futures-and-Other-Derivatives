from abc import ABC


class Asset(ABC):
    def __init__(self, name: str = "default_asset") -> None:
        self.name = name
