"""Synthetic per-house solar generation and consumption.

A small neighbourhood of houses. Some have solar panels (prosumers), some only
consume. Generation follows a daily solar curve scaled by the panel size and the
day's weather; consumption has a base load plus a morning and an evening peak.
Everything is synthetic and deterministic.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def make_houses(n_houses: int = 20, seed: int = 42) -> list[dict]:
    rng = np.random.default_rng(seed)
    houses = []
    for i in range(n_houses):
        has_pv = i % 2 == 0  # half the houses have panels
        houses.append(
            {
                "name": f"house_{i:02d}",
                "pv_capacity_kwh": float(rng.uniform(3.0, 8.0)) if has_pv else 0.0,
                "base_load_kwh": float(rng.uniform(0.3, 0.7)),
            }
        )
    return houses


def _solar_shape(hour: int) -> float:
    # Bell curve from ~6:00 to ~18:00, peak at noon.
    if 6 <= hour <= 18:
        return float(max(0.0, np.sin(np.pi * (hour - 6) / 12)))
    return 0.0


def _consumption(hour: int, base: float, rng: np.random.Generator) -> float:
    load = base
    if 7 <= hour <= 9:
        load += 0.8
    if 18 <= hour <= 22:
        load += 1.2
    load += rng.normal(0, 0.1)
    return float(max(0.05, load))


def make_history(houses: list[dict], days: int = 14, seed: int = 7) -> pd.DataFrame:
    """Return hourly generation and consumption per house over ``days`` days."""
    rng = np.random.default_rng(seed)
    rows = []
    for day in range(days):
        weather = float(rng.uniform(0.5, 1.0))  # cloudiness scales solar
        for hour in range(24):
            solar = _solar_shape(hour) * weather
            for house in houses:
                gen = round(house["pv_capacity_kwh"] * solar, 4)
                cons = round(_consumption(hour, house["base_load_kwh"], rng), 4)
                rows.append(
                    {"house": house["name"], "day": day, "hour": hour,
                     "generation": gen, "consumption": cons, "net": round(gen - cons, 4)}
                )
    return pd.DataFrame(rows)
