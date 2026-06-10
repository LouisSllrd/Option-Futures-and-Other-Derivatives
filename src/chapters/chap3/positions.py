from abc import ABC

import pandas as pd

from chapters.chap3.futures import Future


class Position(ABC):
    def __init__(
        self,
        is_long: bool,
        date: pd.Timestamp,
    ) -> None:
        self.is_long = is_long
        self.date = date


class FuturePosition(Position):
    def __init__(self, is_long: bool, date: pd.Timestamp, future: Future) -> None:
        super().__init__(is_long, date)
        self.future = future
