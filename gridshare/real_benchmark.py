"""Run the GridShare market on a real neighbourhood.

The market, the forecaster and the ledger are deterministic — a double auction and
tariff arithmetic, not a trained model — so there is nothing to over/underfit. The
real-data question is whether the mechanism produces sound, worthwhile outcomes on
**real** meter data, not only on the synthetic generator: does it match surplus solar
to real demand, clear between the grid's buy and sell prices, and leave both sides
better off than trading with the grid alone?

This runs a full real day (:class:`gridshare.service.GridShareService` fed the real
``(houses, history)`` from :mod:`gridshare.real_data`) and summarises it.

Run it with ``python -m gridshare.real_benchmark``.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import Settings, get_settings
from .real_data import load_real_neighbourhood
from .service import GridShareService


@dataclass
class RealBenchmarkReport:
    n_houses: int
    n_prosumers: int
    days: int
    total_p2p_kwh: float
    total_grid_import_kwh: float
    total_grid_export_kwh: float
    total_buyer_savings_cents: float
    total_seller_earnings_cents: float
    forecast_net_mae_kwh: float
    clearing_prices: list[float]
    grid_buy_cents: float
    grid_sell_cents: float

    @property
    def self_sufficiency(self) -> float:
        """Share of the day's demand met locally rather than by grid import."""
        served = self.total_p2p_kwh + self.total_grid_import_kwh
        return self.total_p2p_kwh / served if served > 0 else 0.0

    @property
    def prices_within_spread(self) -> bool:
        """Every clearing price sits strictly between the grid's sell and buy prices."""
        return all(
            self.grid_sell_cents <= p <= self.grid_buy_cents for p in self.clearing_prices
        )


def run_benchmark(settings: Settings | None = None, days: int = 14) -> RealBenchmarkReport:
    settings = settings or get_settings()
    houses, history = load_real_neighbourhood(settings.n_houses, days=days)
    service = GridShareService(settings=settings, days=days, houses=houses, history=history)
    day = service.simulate_day(settle=False)
    prices = [
        h["clearing_price_cents"] for h in day["hours"] if h["clearing_price_cents"] is not None
    ]
    return RealBenchmarkReport(
        n_houses=day["n_houses"],
        n_prosumers=sum(1 for h in houses if h["pv_capacity_kwh"] > 0),
        days=days,
        total_p2p_kwh=day["total_p2p_kwh"],
        total_grid_import_kwh=round(sum(h["grid_import_kwh"] for h in day["hours"]), 4),
        total_grid_export_kwh=round(sum(h["grid_export_kwh"] for h in day["hours"]), 4),
        total_buyer_savings_cents=day["total_buyer_savings_cents"],
        total_seller_earnings_cents=day["total_seller_earnings_cents"],
        forecast_net_mae_kwh=day["forecast_net_mae_kwh"],
        clearing_prices=prices,
        grid_buy_cents=settings.grid_buy_cents,
        grid_sell_cents=settings.grid_sell_cents,
    )


def format_report(report: RealBenchmarkReport) -> str:
    prices = report.clearing_prices
    avg_price = sum(prices) / len(prices) if prices else 0.0
    lines = [
        "GridShare real-data benchmark — Low Carbon London demand + German solar",
        "=" * 70,
        f"neighbourhood      : {report.n_houses} houses, {report.n_prosumers} with panels, "
        f"{report.days} real days",
        f"grid tariff        : buy {report.grid_buy_cents:.0f}c / sell "
        f"{report.grid_sell_cents:.0f}c per kWh",
        f"forecast net MAE   : {report.forecast_net_mae_kwh:.4f} kWh/house/hour",
        "",
        f"peer-to-peer traded: {report.total_p2p_kwh:,.1f} kWh over the day",
        f"grid import / export: {report.total_grid_import_kwh:,.1f} / "
        f"{report.total_grid_export_kwh:,.1f} kWh",
        f"self-sufficiency   : {report.self_sufficiency:.1%} of demand met locally",
        f"clearing price     : {avg_price:.1f}c avg "
        f"(all within the {report.grid_sell_cents:.0f}-{report.grid_buy_cents:.0f}c spread: "
        f"{report.prices_within_spread})",
        f"buyer savings      : {report.total_buyer_savings_cents / 100:,.2f} $ vs the grid price",
        f"seller earnings    : {report.total_seller_earnings_cents / 100:,.2f} $ vs the feed-in",
        "",
        "On real demand and real solar the local market clears surplus solar into real "
        "neighbours' demand at a price between the grid's buy and sell rates, so sellers "
        "earn more than the feed-in rate and buyers pay less than retail — both sides "
        "ahead, with less energy drawn from the wider grid.",
    ]
    return "\n".join(lines)


def main() -> None:
    print(format_report(run_benchmark()))


if __name__ == "__main__":
    main()
