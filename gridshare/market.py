"""A uniform-price double auction for a local energy market.

Each hour, houses with surplus solar are sellers and houses with a deficit are
buyers. A peer trade is good for both sides: the seller earns more than the grid
feed-in price, and the buyer pays less than the grid retail price. We match them
with a double auction: sort buyers by bid (high to low) and sellers by ask (low
to high), match while a buyer still beats a seller, and settle all matched energy
at one clearing price (the midpoint of the last matched pair). Whatever is left
trades with the grid.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Order:
    house: str
    kwh: float
    price: float  # cents/kWh: a bid for a buyer, an ask for a seller


@dataclass
class Trade:
    buyer: str
    seller: str
    kwh: float
    price: float  # clearing price, cents/kWh


@dataclass
class MarketResult:
    trades: list[Trade]
    clearing_price: float | None
    p2p_kwh: float
    grid_import_kwh: float
    grid_export_kwh: float
    buyer_savings_cents: float
    seller_earnings_cents: float


def clear_market(
    bids: list[Order], asks: list[Order], grid_buy_cents: float, grid_sell_cents: float
) -> MarketResult:
    bids = sorted(bids, key=lambda o: o.price, reverse=True)
    asks = sorted(asks, key=lambda o: o.price)

    demand = sum(b.kwh for b in bids)
    supply = sum(a.kwh for a in asks)

    trades: list[Trade] = []
    clearing_price: float | None = None
    bi = ai = 0
    b_rem = bids[bi].kwh if bids else 0.0
    a_rem = asks[ai].kwh if asks else 0.0

    while bi < len(bids) and ai < len(asks) and bids[bi].price >= asks[ai].price:
        qty = min(b_rem, a_rem)
        clearing_price = round((bids[bi].price + asks[ai].price) / 2, 2)
        trades.append(
            Trade(
                buyer=bids[bi].house, seller=asks[ai].house, kwh=round(qty, 4), price=clearing_price
            )
        )
        b_rem -= qty
        a_rem -= qty
        if b_rem <= 1e-9:
            bi += 1
            b_rem = bids[bi].kwh if bi < len(bids) else 0.0
        if a_rem <= 1e-9:
            ai += 1
            a_rem = asks[ai].kwh if ai < len(asks) else 0.0

    # Price the settled trades at a single clearing price.
    price = clearing_price if clearing_price is not None else (grid_buy_cents + grid_sell_cents) / 2
    for trade in trades:
        trade.price = price

    p2p_kwh = round(sum(t.kwh for t in trades), 4)
    grid_import = round(max(0.0, demand - p2p_kwh), 4)
    grid_export = round(max(0.0, supply - p2p_kwh), 4)

    # Savings vs trading only with the grid.
    buyer_savings = round(p2p_kwh * (grid_buy_cents - price), 2)
    seller_earnings = round(p2p_kwh * (price - grid_sell_cents), 2)

    return MarketResult(
        trades=trades,
        clearing_price=price if trades else None,
        p2p_kwh=p2p_kwh,
        grid_import_kwh=grid_import,
        grid_export_kwh=grid_export,
        buyer_savings_cents=buyer_savings,
        seller_earnings_cents=seller_earnings,
    )
