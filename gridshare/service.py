"""Run the market: forecast, clear the auction, and settle trades on-chain."""

from __future__ import annotations

from .chain.ledger import InMemoryLedgerClient, LedgerClient, house_id
from .config import Settings, get_settings
from .forecast import HourlyMeanForecaster
from .generate import make_history, make_houses
from .market import Order, clear_market


class GridShareService:
    def __init__(
        self,
        settings: Settings | None = None,
        ledger: LedgerClient | None = None,
        days: int = 14,
    ) -> None:
        self.settings = settings or get_settings()
        self.houses = make_houses(self.settings.n_houses, seed=42)
        self.history = make_history(self.houses, days=days, seed=7)
        self.sim_day = int(self.history["day"].max())
        train = self.history[self.history["day"] < self.sim_day]
        self.forecaster = HourlyMeanForecaster().fit(train)
        self.ledger = ledger if ledger is not None else self._build_ledger()

    def _build_ledger(self) -> LedgerClient:
        if (
            self.settings.chain_enabled
            and self.settings.contract_address
            and self.settings.chain_private_key
        ):
            from web3 import Web3

            from .chain.ledger import Web3LedgerClient

            w3 = Web3(Web3.HTTPProvider(self.settings.chain_rpc_url))
            account = w3.eth.account.from_key(self.settings.chain_private_key).address
            return Web3LedgerClient(
                w3, self.settings.contract_address, account, self.settings.chain_private_key
            )
        return InMemoryLedgerClient()

    @staticmethod
    def _margin(house: str) -> float:
        # A deterministic 0..15 margin per house, so bids and asks vary and the
        # clearing price is not always the exact midpoint.
        return float(sum(ord(c) for c in house) % 16)

    def _orders_for_hour(self, hour: int) -> tuple[list[Order], list[Order]]:
        day = self.history[(self.history["day"] == self.sim_day) & (self.history["hour"] == hour)]
        bids: list[Order] = []
        asks: list[Order] = []
        for _, row in day.iterrows():
            net = float(row["net"])
            margin = self._margin(row["house"])
            if net < -1e-6:  # deficit -> buyer, bids below the grid retail price
                bids.append(
                    Order(house=row["house"], kwh=-net, price=self.settings.grid_buy_cents - margin)
                )
            elif net > 1e-6:  # surplus -> seller, asks above the grid feed-in price
                asks.append(
                    Order(house=row["house"], kwh=net, price=self.settings.grid_sell_cents + margin)
                )
        return bids, asks

    def simulate_hour(self, hour: int, settle: bool = True) -> dict:
        bids, asks = self._orders_for_hour(hour)
        result = clear_market(
            bids, asks, self.settings.grid_buy_cents, self.settings.grid_sell_cents
        )

        settled = 0
        if settle:
            for trade in result.trades:
                kwh_milli = int(round(trade.kwh * 1000))
                if kwh_milli <= 0:
                    continue
                self.ledger.settle(
                    house_id(trade.buyer),
                    house_id(trade.seller),
                    kwh_milli,
                    int(round(trade.price)),
                    hour,
                )
                settled += 1

        return {
            "hour": hour,
            "clearing_price_cents": result.clearing_price,
            "p2p_kwh": result.p2p_kwh,
            "grid_import_kwh": result.grid_import_kwh,
            "grid_export_kwh": result.grid_export_kwh,
            "buyer_savings_cents": result.buyer_savings_cents,
            "seller_earnings_cents": result.seller_earnings_cents,
            "trades": [
                {"buyer": t.buyer, "seller": t.seller, "kwh": t.kwh, "price_cents": t.price}
                for t in result.trades
            ],
            "settled_on_chain": settled,
            "contract_address": self.ledger.address,
        }

    def simulate_day(self, settle: bool = False) -> dict:
        hours = [self.simulate_hour(h, settle=settle) for h in range(24)]
        total_p2p = round(sum(h["p2p_kwh"] for h in hours), 4)
        total_savings = round(sum(h["buyer_savings_cents"] for h in hours), 2)
        total_earnings = round(sum(h["seller_earnings_cents"] for h in hours), 2)
        actual = self.history[self.history["day"] == self.sim_day]
        return {
            "n_houses": len(self.houses),
            "total_p2p_kwh": total_p2p,
            "total_buyer_savings_cents": total_savings,
            "total_seller_earnings_cents": total_earnings,
            "forecast_net_mae_kwh": round(self.forecaster.mae(actual), 4),
            "hours": hours,
        }
