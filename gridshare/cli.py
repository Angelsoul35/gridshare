"""GridShare command-line demo."""

from __future__ import annotations

import argparse

from web3 import EthereumTesterProvider, Web3

from .chain.ledger import Web3LedgerClient, deploy_ledger, house_id
from .config import get_settings
from .service import GridShareService


def demo() -> None:
    settings = get_settings()

    print("1) Deploying GridLedger to an in-memory EVM ...")
    w3 = Web3(EthereumTesterProvider())
    deployer = w3.eth.accounts[0]
    address = deploy_ledger(w3, deployer)
    ledger = Web3LedgerClient(w3, address, deployer)
    print(f"   ledger at {address}")

    service = GridShareService(settings=settings, ledger=ledger)

    print("2) Simulating a day of the local market ...")
    day = service.simulate_day(settle=True)
    print(f"   {day['n_houses']} houses")
    print(f"   peer-to-peer energy traded: {day['total_p2p_kwh']:.2f} kWh")
    print(f"   buyer savings: {day['total_buyer_savings_cents'] / 100:,.2f}")
    print(f"   seller extra earnings: {day['total_seller_earnings_cents'] / 100:,.2f}")
    print(f"   forecast net MAE: {day['forecast_net_mae_kwh']:.3f} kWh")

    print("3) A sample midday hour (high solar):")
    noon = next(h for h in day["hours"] if h["hour"] == 12)
    print(f"   clearing price: {noon['clearing_price_cents']} cents/kWh")
    print(
        f"   p2p {noon['p2p_kwh']:.2f} kWh in {len(noon['trades'])} trades, "
        f"{noon['settled_on_chain']} settled on-chain"
    )

    print("4) On-chain positions (net kWh) for the first two houses:")
    for house in service.houses[:2]:
        pos = ledger.position_of(house_id(house["name"]))
        print(
            f"   {house['name']}: net {pos.net_kwh_milli / 1000:+.2f} kWh, "
            f"net {pos.net_cents / 100:+.2f} over {pos.trades} trades"
        )
    print(f"   total trades on-chain: {ledger.total_trades()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="GridShare CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("demo", help="deploy, simulate a day, and settle on-chain")
    args = parser.parse_args()
    if args.command == "demo":
        demo()


if __name__ == "__main__":
    main()
