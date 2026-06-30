import numpy as np
import pandas as pd


class Timeserie:
    """
    Thin wrapper around a DataFrame with columns ['Date', 'Price'].
    """

    REQUIRED_COLUMNS = ["Date", "Price"]

    def __init__(self, df: pd.DataFrame | None = None) -> None:
        if df is None:
            self.df = pd.DataFrame(columns=self.REQUIRED_COLUMNS)
        else:
            for col in self.REQUIRED_COLUMNS:
                if col not in df.columns:
                    raise ValueError(
                        f"A timeserie dataframe should contain column {col}."
                    )
            self.df = df.sort_values("Date").reset_index(drop=True)

    @property
    def last_price(self) -> float:
        if self.df.empty:
            raise ValueError("Cannot get last_price of an empty Timeserie.")
        return float(self.df["Price"].iloc[-1])

    def price_at(self, date: pd.Timestamp) -> float:
        """Returns the price at (or immediately before) the given date."""
        eligible = self.df[self.df["Date"] <= date]
        if eligible.empty:
            raise ValueError(f"No price available at or before {date}.")
        return float(eligible["Price"].iloc[-1])

    def price_changes(self) -> pd.Series:
        """Absolute price changes between consecutive observations (Delta S / Delta F)."""
        return self.df["Price"].diff().dropna()

    def ar_returns(self) -> pd.Series:
        """Percentage (one-day) price changes, used for the 'tailed' hedge ratio."""
        return self.df["Price"].pct_change().dropna()

    def historical_volatility(self, pct: bool = False) -> float:
        series = self.ar_returns() if pct else self.price_changes()
        return float(series.std())

    @staticmethod
    def correlation(a: "Timeserie", b: "Timeserie", pct: bool = False) -> float:
        """Correlation coefficient (rho) between the changes of two timeseries."""
        sa = a.ar_returns() if pct else a.price_changes()
        sb = b.ar_returns() if pct else b.price_changes()
        n = min(len(sa), len(sb))
        return float(np.corrcoef(sa.iloc[-n:], sb.iloc[-n:])[0, 1])
