"""Forecast each house's net energy for an hour of the day.

The market needs to know, ahead of time, which houses will have surplus solar and
which will need energy. We forecast with a simple, honest baseline: the average
generation and consumption for each house at each hour of the day, learned from
history. It is easy to explain and a fair starting point; a stronger model could
replace it behind the same interface.
"""

from __future__ import annotations

import pandas as pd


class HourlyMeanForecaster:
    def __init__(self) -> None:
        self._gen: dict[tuple[str, int], float] = {}
        self._cons: dict[tuple[str, int], float] = {}

    def fit(self, history: pd.DataFrame) -> HourlyMeanForecaster:
        gen = history.groupby(["house", "hour"])["generation"].mean()
        cons = history.groupby(["house", "hour"])["consumption"].mean()
        self._gen = {(h, hr): float(v) for (h, hr), v in gen.items()}
        self._cons = {(h, hr): float(v) for (h, hr), v in cons.items()}
        return self

    def forecast_net(self, house: str, hour: int) -> float:
        gen = self._gen.get((house, hour), 0.0)
        cons = self._cons.get((house, hour), 0.0)
        return round(gen - cons, 4)

    def mae(self, actual: pd.DataFrame) -> float:
        """Mean absolute error of the net forecast against actual rows."""
        errors = []
        for _, row in actual.iterrows():
            predicted = self.forecast_net(row["house"], int(row["hour"]))
            errors.append(abs(predicted - row["net"]))
        return float(sum(errors) / len(errors)) if errors else 0.0
