from __future__ import annotations

from gridshare.forecast import HourlyMeanForecaster
from gridshare.generate import make_history, make_houses
from gridshare.market import Order, clear_market


def test_houses_split_prosumers_and_consumers():
    houses = make_houses(20, seed=42)
    assert len(houses) == 20
    with_pv = [h for h in houses if h["pv_capacity_kwh"] > 0]
    assert 5 <= len(with_pv) <= 15  # roughly half


def test_history_has_no_solar_at_night():
    houses = make_houses(6, seed=1)
    history = make_history(houses, days=2, seed=2)
    night = history[history["hour"] == 2]
    assert night["generation"].sum() == 0.0
    noon = history[history["hour"] == 12]
    assert noon["generation"].sum() > 0.0


def test_forecaster_learns_and_scores():
    houses = make_houses(6, seed=1)
    history = make_history(houses, days=6, seed=2)
    train = history[history["day"] < 5]
    forecaster = HourlyMeanForecaster().fit(train)
    net = forecaster.forecast_net(houses[0]["name"], 12)
    assert isinstance(net, float)
    mae = forecaster.mae(history[history["day"] == 5])
    assert mae >= 0.0


def test_market_clears_and_computes_savings():
    bids = [Order("b1", kwh=3.0, price=75), Order("b2", kwh=2.0, price=70)]
    asks = [Order("s1", kwh=4.0, price=30), Order("s2", kwh=1.0, price=35)]
    result = clear_market(bids, asks, grid_buy_cents=80, grid_sell_cents=20)
    assert result.p2p_kwh == 5.0  # all demand met by supply
    assert result.clearing_price is not None
    assert 20 < result.clearing_price < 80
    assert result.buyer_savings_cents > 0
    assert result.seller_earnings_cents > 0


def test_market_no_cross():
    # A buyer who bids below every ask -> no trade.
    bids = [Order("b1", kwh=3.0, price=25)]
    asks = [Order("s1", kwh=3.0, price=40)]
    result = clear_market(bids, asks, grid_buy_cents=80, grid_sell_cents=20)
    assert result.trades == []
    assert result.p2p_kwh == 0.0


def test_market_empty():
    result = clear_market([], [], grid_buy_cents=80, grid_sell_cents=20)
    assert result.p2p_kwh == 0.0
    assert result.clearing_price is None
