import json
from pathlib import Path

import pandas as pd

from chapters.chap3.futures import Asset, Commodity, Future, Stock, Timeserie

DATABASE_DIR = Path(__file__).parent.parent.parent / "Database"


class DatabaseConnection:
    """
    Connection to the local JSON Database.

    Loads the 3 files (commodities.json, stocks.json, futures.json)
    into memory at instantiation time, then exposes lookup methods
    to retrieve rebuilt business objects.
    """

    def __init__(self, database_dir: Path = DATABASE_DIR) -> None:
        self.database_dir = database_dir
        self._commodities_raw = self._load_json("commodities.json")
        self._stocks_raw = self._load_json("stocks.json")
        self._futures_raw = self._load_json("futures.json")

    def _load_json(self, filename: str) -> dict:
        path = self.database_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        with open(path, "r") as f:
            return json.load(f)

    # -- Object reconstruction ------------------------------------------

    @staticmethod
    def _build_timeserie(raw_timeserie: dict) -> Timeserie:
        df = pd.DataFrame(
            {
                "Date": pd.to_datetime(raw_timeserie["Date"]),
                "Price": raw_timeserie["Price"],
            }
        )
        return Timeserie(df=df)

    def get_commodity(self, name: str) -> Commodity:
        if name not in self._commodities_raw:
            raise KeyError(f"Commodity '{name}' not found in the database.")
        raw = self._commodities_raw[name]
        return Commodity(
            name=raw["name"],
            spot_prices=self._build_timeserie(raw["spot_prices"]),
        )

    def get_stock(self, name: str) -> Stock:
        if name not in self._stocks_raw:
            raise KeyError(f"Stock '{name}' not found in the database.")
        raw = self._stocks_raw[name]
        return Stock(
            name=raw["name"],
            prices=self._build_timeserie(raw["prices"]),
        )

    def get_asset(self, name: str, asset_type: str) -> Asset:
        """Generic lookup used to resolve a Future's underlying."""
        if asset_type == "commodity":
            return self.get_commodity(name)
        elif asset_type == "stock":
            return self.get_stock(name)
        raise ValueError(f"Unknown asset type: '{asset_type}'")

    def get_future(self, name: str) -> Future:
        if name not in self._futures_raw:
            raise KeyError(f"Future '{name}' not found in the database.")
        raw = self._futures_raw[name]
        underlying = self.get_asset(raw["underlying_name"], raw["underlying_type"])
        return Future(
            underlying=underlying,
            contract_price=raw["contract_price"],
            maturity=pd.Timestamp(raw["maturity"]),
            contract_size=raw["contract_size"],
        )

    # -- Listing ----------------------------------------------------------

    def list_commodities(self) -> list[str]:
        return list(self._commodities_raw.keys())

    def list_stocks(self) -> list[str]:
        return list(self._stocks_raw.keys())

    def list_futures(self) -> list[str]:
        return list(self._futures_raw.keys())
