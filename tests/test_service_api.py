from __future__ import annotations

from fastapi.testclient import TestClient
from web3 import EthereumTesterProvider, Web3

from gridshare.chain.ledger import Web3LedgerClient, deploy_ledger
from gridshare.config import Settings
from gridshare.service import GridShareService


def test_simulate_hour_structure(service):
    result = service.simulate_hour(12, settle=True)
    assert result["hour"] == 12
    assert result["p2p_kwh"] >= 0
    assert "trades" in result
    if result["trades"]:
        assert result["clearing_price_cents"] is not None


def test_simulate_day_aggregates(service):
    day = service.simulate_day(settle=False)
    assert day["n_houses"] == 20
    assert day["total_p2p_kwh"] > 0
    assert day["total_buyer_savings_cents"] >= 0
    assert day["forecast_net_mae_kwh"] >= 0
    assert len(day["hours"]) == 24


def test_settlement_reaches_the_chain():
    w3 = Web3(EthereumTesterProvider())
    account = w3.eth.accounts[0]
    ledger = Web3LedgerClient(w3, deploy_ledger(w3, account), account)
    settings = Settings(chain_enabled=False)
    service = GridShareService(settings=settings, ledger=ledger, days=8)

    result = service.simulate_hour(12, settle=True)
    assert result["settled_on_chain"] == len(result["trades"])
    assert ledger.total_trades() == result["settled_on_chain"]


def test_api(service):
    import gridshare.main as main

    main._service = service
    client = TestClient(main.app)

    assert client.get("/health").json() == {"status": "ok"}

    hour = client.post("/simulate/hour", json={"hour": 12, "settle": True})
    assert hour.status_code == 200
    assert hour.json()["hour"] == 12

    day = client.get("/simulate/day")
    assert day.status_code == 200
    assert day.json()["n_houses"] == 20

    assert client.post("/simulate/hour", json={"hour": 30}).status_code == 422
