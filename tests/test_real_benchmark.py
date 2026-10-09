"""Functional tests for the real-neighbourhood benchmark.

GridShare's market is deterministic, so these do not check an accuracy number; they
prove the mechanism produces sound outcomes on **real** meter data: the real history is
well-formed, the market clears strictly inside the grid's price spread, both sides come
out ahead, and the economics respond correctly to the inputs (no spread -> no savings;
a controlled real-shaped history yields exactly the matching trade).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from gridshare.config import Settings
from gridshare.real_benchmark import format_report, run_benchmark
from gridshare.real_data import load_real_neighbourhood
from gridshare.service import GridShareService


@pytest.fixture(scope="module")
def neighbourhood():
    return load_real_neighbourhood(n_houses=20, days=14)


@pytest.fixture(scope="module")
def report():
    return run_benchmark(days=14)


def test_real_history_is_well_formed(neighbourhood):
    houses, history = neighbourhood
    assert len(houses) == 20
    assert set(history.columns) == {"house", "day", "hour", "generation", "consumption", "net"}
    assert len(history) == 20 * 14 * 24
    # Accounting identity and non-negativity on real data.
    assert np.allclose(history["net"], history["generation"] - history["consumption"], atol=1e-6)
    assert (history["generation"] >= 0).all()
    assert (history["consumption"] > 0).all()  # a real home always draws some power


def test_prosumers_generate_at_midday_others_never(neighbourhood):
    houses, history = neighbourhood
    prosumers = {h["name"] for h in houses if h["pv_capacity_kwh"] > 0}
    non = {h["name"] for h in houses if h["pv_capacity_kwh"] == 0}
    assert len(prosumers) == 10 and len(non) == 10
    midday = history[history["hour"] == 12]
    assert (midday[midday["house"].isin(prosumers)]["generation"] > 0).any()
    # Houses without panels never generate, at any hour.
    assert (history[history["house"].isin(non)]["generation"] == 0).all()


def test_market_clears_inside_the_spread_and_both_sides_win(report):
    assert report.total_p2p_kwh > 0  # real surplus solar meets real demand
    assert report.clearing_prices  # at least one hour matched
    assert report.prices_within_spread  # sell <= price <= buy for every hour
    # The economic invariant of a local market: both sides beat trading with the grid.
    assert report.total_buyer_savings_cents > 0
    assert report.total_seller_earnings_cents > 0
    assert 0 < report.self_sufficiency < 1


def test_no_spread_means_no_savings():
    """If the grid buy and sell prices meet, the clearing price equals both and the
    local market offers no advantage — savings and earnings collapse to zero."""
    flat = Settings(grid_buy_cents=50.0, grid_sell_cents=50.0)
    rep = run_benchmark(settings=flat, days=14)
    spread = run_benchmark(settings=Settings(grid_buy_cents=80.0, grid_sell_cents=20.0), days=14)
    # With a real spread there is a local advantage; with none it vanishes.
    assert spread.total_buyer_savings_cents > 0
    assert rep.total_buyer_savings_cents == pytest.approx(0.0, abs=1e-6)
    assert rep.total_seller_earnings_cents == pytest.approx(0.0, abs=1e-6)


def test_controlled_injection_yields_the_matching_trade():
    """Inject a two-house, one-hour real-shaped history: a surplus seller and a deficit
    buyer must produce exactly one matched trade inside the spread."""
    houses = [
        {"name": "seller", "pv_capacity_kwh": 5.0, "base_load_kwh": 0.3},
        {"name": "buyer", "pv_capacity_kwh": 0.0, "base_load_kwh": 0.3},
    ]
    history = pd.DataFrame(
        [
            {"house": "seller", "day": 0, "hour": 12, "generation": 4.0,
             "consumption": 1.0, "net": 3.0},
            {"house": "buyer", "day": 0, "hour": 12, "generation": 0.0,
             "consumption": 2.0, "net": -2.0},
        ]
    )
    service = GridShareService(settings=Settings(), days=1, houses=houses, history=history)
    out = service.simulate_hour(12, settle=False)
    assert len(out["trades"]) == 1
    trade = out["trades"][0]
    assert trade["buyer"] == "buyer" and trade["seller"] == "seller"
    assert trade["kwh"] == pytest.approx(2.0)  # min(surplus 3, deficit 2)
    assert Settings().grid_sell_cents <= trade["price_cents"] <= Settings().grid_buy_cents


def test_injecting_history_without_houses_is_rejected():
    with pytest.raises(ValueError):
        GridShareService(history=pd.DataFrame({"house": []}))


def test_format_report_renders_the_summary(report):
    text = format_report(report)
    assert "real-data benchmark" in text
    assert "self-sufficiency" in text
    assert "peer-to-peer" in text


def test_main_prints_the_report(capsys):
    from gridshare.real_benchmark import main

    main()
    assert "real-data benchmark" in capsys.readouterr().out


def test_loader_rejects_a_missing_dataset(monkeypatch, tmp_path):
    import gridshare.real_data as rd

    monkeypatch.setattr(rd, "_DATASET_PATH", tmp_path / "missing.npz")
    with pytest.raises(FileNotFoundError):
        rd.load_real_neighbourhood()


def test_fetch_builds_the_npz(tmp_path, monkeypatch):
    import gridshare.real_data as rd

    london_rows = {
        "rows": [
            {"row": {"item_id": "MAC0001", "target": [0.2] * 48}},
            {"row": {"item_id": "MAC0002", "target": [0.3] * 48}},
        ]
    }
    solar_rows = {"rows": [{"row": {"supplier_50hertz": float(v)}} for v in range(24)]}

    def fake_get(ds, off, ln=100, tries=5):
        if ds == rd._LONDON:
            return london_rows if off == 0 else {"rows": []}
        return solar_rows if off == 165 * 24 else {"rows": []}

    monkeypatch.setattr(rd, "_get", fake_get)
    dest = tmp_path / "n.npz"
    n_homes, n_hours = rd.fetch_neighbourhood(n_houses=2, days=1, dest=dest)
    assert (n_homes, n_hours) == (2, 24)
    data = np.load(dest, allow_pickle=True)
    assert data["consumption"].shape == (2, 24)
    # Two 0.2 kWh half-hours -> 0.4 kWh per hour for the first home.
    assert data["consumption"][0].tolist() == [0.4] * 24
    assert data["solar_cf"].max() <= 1.2 and data["solar_cf"].min() == 0.0
