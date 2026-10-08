from __future__ import annotations

import pytest
from eth_tester.exceptions import TransactionFailed
from web3.exceptions import ContractLogicError

from gridshare.chain.ledger import (
    InMemoryLedgerClient,
    Web3LedgerClient,
    deploy_ledger,
    house_id,
)

pytestmark = pytest.mark.chain

REVERT_ERRORS = (ContractLogicError, TransactionFailed)


def test_settle_updates_positions(ledger):
    buyer, seller = house_id("house_a"), house_id("house_b")
    receipt = ledger.settle(buyer, seller, 2500, 50, 12)  # 2.5 kWh at 50 c/kWh
    assert receipt.index == 0
    assert ledger.total_trades() == 1

    b = ledger.position_of(buyer)
    s = ledger.position_of(seller)
    assert b.net_kwh_milli == 2500 and b.net_cents == -125  # 2500*50/1000
    assert s.net_kwh_milli == -2500 and s.net_cents == 125


def test_settle_rejects_same_party(ledger):
    same = house_id("house_a")
    with pytest.raises(REVERT_ERRORS):
        ledger.settle(same, same, 1000, 50, 1)


def test_only_operator_can_settle(w3):
    owner, outsider = w3.eth.accounts[0], w3.eth.accounts[1]
    address = deploy_ledger(w3, owner)
    rogue = Web3LedgerClient(w3, address, outsider)
    with pytest.raises(REVERT_ERRORS):
        rogue.settle(house_id("a"), house_id("b"), 1000, 50, 1)


def test_in_memory_matches_contract(ledger):
    buyer, seller = house_id("x"), house_id("y")
    ledger.settle(buyer, seller, 3000, 40, 9)
    mem = InMemoryLedgerClient()
    mem.settle(buyer, seller, 3000, 40, 9)
    assert mem.position_of(buyer).net_kwh_milli == ledger.position_of(buyer).net_kwh_milli
    assert mem.position_of(buyer).net_cents == ledger.position_of(buyer).net_cents
    assert mem.total_trades() == ledger.total_trades()
