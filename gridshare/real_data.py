"""A real neighbourhood for GridShare, built from measured meter data.

The synthetic generator (:mod:`gridshare.generate`) is deterministic, which is ideal
for tests. This module builds the same ``(houses, history)`` pair from **real**
measurements instead, so the market, the forecaster and the ledger run on data no one
designed:

* **Consumption** — real hourly household electricity use from the Low Carbon London
  smart-meter trial (via the Hugging Face ``eeJunCao/London_smart_meter`` mirror), one
  real metered home per house.
* **Generation** — a real solar **capacity-factor** profile (0 at night, ~1 at solar
  noon) taken from measured German grid PV output (``sashamn/germany-solar-generation``,
  50Hertz zone, a summer fortnight), scaled by each prosumer's panel size.

Each house therefore pairs one real consumption trace with a real solar shape scaled to
its panels — a real-data basis for the local market. The vendored arrays live in
``datasets/neighbourhood_real.npz``; ``fetch_neighbourhood`` refreshes them.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .generate import make_houses

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DATASET_PATH = _REPO_ROOT / "datasets" / "neighbourhood_real.npz"

_LONDON = "eeJunCao%2FLondon_smart_meter"
_SOLAR = "sashamn%2Fgermany-solar-generation"
_ROWS = (
    "https://datasets-server.huggingface.co/rows?dataset={ds}"
    "&config=default&split=train&offset={off}&length={ln}"
)


def load_real_neighbourhood(n_houses: int = 20, days: int = 14) -> tuple[list[dict], pd.DataFrame]:
    """Return ``(houses, history)`` built from the vendored real measurements.

    ``houses`` reuses GridShare's house definitions (names, panel sizes); ``history`` is
    the long per-house hourly frame (``house, day, hour, generation, consumption, net``)
    the rest of GridShare consumes — here filled with real data.
    """
    if not _DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Vendored neighbourhood not found at {_DATASET_PATH}. Refresh it with "
            "gridshare.real_data.fetch_neighbourhood()."
        )
    data = np.load(_DATASET_PATH, allow_pickle=True)
    consumption = data["consumption"]  # (homes, days*24) real kWh/h
    solar_cf = data["solar_cf"]  # (days*24,) real capacity factor 0..~1
    hours = days * 24
    if consumption.shape[0] < n_houses or consumption.shape[1] < hours or solar_cf.shape[0] < hours:
        raise ValueError("vendored data is smaller than the requested neighbourhood")

    houses = make_houses(n_houses, seed=42)
    rows = []
    for idx, house in enumerate(houses):
        cons_series = consumption[idx]
        cap = house["pv_capacity_kwh"]
        for day in range(days):
            for hour in range(24):
                t = day * 24 + hour
                gen = round(cap * float(solar_cf[t]), 4)  # 0 for non-prosumers (cap=0)
                cons = round(float(cons_series[t]), 4)
                rows.append(
                    {
                        "house": house["name"],
                        "day": day,
                        "hour": hour,
                        "generation": gen,
                        "consumption": cons,
                        "net": round(gen - cons, 4),
                    }
                )
    return houses, pd.DataFrame(rows)


def _get(ds: str, off: int, ln: int = 100, tries: int = 5) -> dict:
    import json
    import time
    import urllib.request

    url = _ROWS.format(ds=ds, off=off, ln=ln)
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=60) as resp:
                return json.load(resp)
        except Exception:  # noqa: BLE001 - network retry
            if i == tries - 1:
                raise
            time.sleep(2**i)
    return {}


def fetch_neighbourhood(
    n_houses: int = 20, days: int = 14, dest: str | Path | None = None
) -> tuple[int, int]:
    """Download real consumption + a real solar profile into the vendored npz.

    Returns ``(n_homes, n_hours)``. Needs the Hugging Face datasets-server.
    """
    target = Path(dest) if dest is not None else _DATASET_PATH
    hours = days * 24
    half = days * 48

    consumption: list[np.ndarray] = []
    home_ids: list[str] = []
    off = 0
    while len(consumption) < n_houses and off < 600:
        rows = _get(_LONDON, off, ln=50).get("rows", [])
        if not rows:
            break
        for row in rows:
            t = np.asarray(row["row"]["target"], dtype=float)[:half]
            if t.shape[0] < half or np.isnan(t).any() or (t < 0).any() or t.sum() <= 0:
                continue
            consumption.append(np.round(t.reshape(-1, 2).sum(axis=1), 4))
            home_ids.append(str(row["row"]["item_id"]))
            if len(consumption) >= n_houses:
                break
        off += 50

    gen: list[float] = []
    off = 165 * 24  # a summer fortnight (mid-June 2012)
    while len(gen) < hours:
        rows = _get(_SOLAR, off, ln=100).get("rows", [])
        if not rows:
            break
        for row in rows:
            gen.append(float(row["row"]["supplier_50hertz"]))
            if len(gen) >= hours:
                break
        off += 100
    gen_arr = np.asarray(gen[:hours], dtype=float)
    solar_cf = np.round(np.clip(gen_arr / np.percentile(gen_arr, 99), 0.0, 1.2), 4)

    target.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        target,
        consumption=np.vstack(consumption),
        solar_cf=solar_cf,
        home_ids=np.array(home_ids),
    )
    return len(consumption), hours
