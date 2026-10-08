from __future__ import annotations

import pytest
from web3 import EthereumTesterProvider, Web3

from gridshare.chain.ledger import Web3LedgerClient, deploy_ledger
from gridshare.config import Settings
from gridshare.service import GridShareService


@pytest.fixture
def w3():
    return Web3(EthereumTesterProvider())


@pytest.fixture
def ledger(w3):
    account = w3.eth.accounts[0]
    address = deploy_ledger(w3, account)
    return Web3LedgerClient(w3, address, account)


@pytest.fixture
def settings():
    return Settings(n_houses=20, grid_buy_cents=80.0, grid_sell_cents=20.0, chain_enabled=False)


@pytest.fixture
def service(settings):
    # In-memory ledger by default (chain disabled), fast to build.
    return GridShareService(settings=settings, days=10)
