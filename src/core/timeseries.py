import pandas as pd


class Timeserie:
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
            self.df = df
