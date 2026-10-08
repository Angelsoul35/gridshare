"""Ledger clients: a Web3-backed client and an in-memory fake.

Both implement :class:`LedgerClient`, so the market can settle trades against the
real compiled contract (on Anvil or an in-memory PyEVM node) or against an
in-memory fake with the same behaviour. Houses are identified by a bytes32 id
(a hash of the house name), so no names reach the chain.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from eth_utils import keccak
from web3 import Web3
from web3.contract import Contract

from .artifacts import contract_abi, contract_bytecode


def house_id(name: str) -> bytes:
    """Return the 32-byte on-chain id for a house name."""
    return keccak(text=name)


@dataclass(frozen=True)
class SettleReceipt:
    index: int
    tx_hash: str | None


@dataclass(frozen=True)
class Position:
    net_kwh_milli: int
    net_cents: int
    trades: int


@runtime_checkable
class LedgerClient(Protocol):
    @property
    def address(self) -> str: ...

    def settle(
        self, buyer: bytes, seller: bytes, kwh_milli: int, price_cents: int, hour: int
    ) -> SettleReceipt: ...

    def position_of(self, party: bytes) -> Position: ...

    def total_trades(self) -> int: ...


class InMemoryLedgerClient:
    """A dict-backed ledger that mirrors the contract's accounting."""

    def __init__(self) -> None:
        self._positions: dict[bytes, list[int]] = {}
        self._total = 0

    @property
    def address(self) -> str:
        return "0x0000000000000000000000000000000000000000"

    def _pos(self, party: bytes) -> list[int]:
        return self._positions.setdefault(party, [0, 0, 0])

    def settle(self, buyer, seller, kwh_milli, price_cents, hour) -> SettleReceipt:
        if buyer == bytes(32) or seller == bytes(32):
            raise ValueError("zero party")
        if buyer == seller:
            raise ValueError("same party")
        if kwh_milli == 0:
            raise ValueError("zero energy")
        cents = (kwh_milli * price_cents) // 1000
        s = self._pos(seller)
        s[0] -= kwh_milli
        s[1] += cents
        s[2] += 1
        b = self._pos(buyer)
        b[0] += kwh_milli
        b[1] -= cents
        b[2] += 1
        index = self._total
        self._total += 1
        return SettleReceipt(index=index, tx_hash=None)

    def position_of(self, party) -> Position:
        p = self._positions.get(party, [0, 0, 0])
        return Position(net_kwh_milli=p[0], net_cents=p[1], trades=p[2])

    def total_trades(self) -> int:
        return self._total


def deploy_ledger(w3: Web3, deployer: str, private_key: str | None = None) -> str:
    deployer = Web3.to_checksum_address(deployer)
    factory = w3.eth.contract(abi=contract_abi(), bytecode=contract_bytecode())
    if private_key:
        tx = factory.constructor().build_transaction(
            {"from": deployer, "nonce": w3.eth.get_transaction_count(deployer)}
        )
        signed = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    else:
        tx_hash = factory.constructor().transact({"from": deployer})
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    return receipt["contractAddress"]


class Web3LedgerClient:
    def __init__(
        self, w3: Web3, contract_address: str, account: str, private_key: str | None = None
    ) -> None:
        self._w3 = w3
        self._account = Web3.to_checksum_address(account)
        self._private_key = private_key
        self._contract: Contract = w3.eth.contract(
            address=Web3.to_checksum_address(contract_address), abi=contract_abi()
        )

    @property
    def address(self) -> str:
        return self._contract.address

    def settle(self, buyer, seller, kwh_milli, price_cents, hour) -> SettleReceipt:
        fn = self._contract.functions.settle(buyer, seller, kwh_milli, price_cents, hour)
        if self._private_key:
            tx = fn.build_transaction(
                {"from": self._account, "nonce": self._w3.eth.get_transaction_count(self._account)}
            )
            signed = self._w3.eth.account.sign_transaction(tx, self._private_key)
            tx_hash = self._w3.eth.send_raw_transaction(signed.raw_transaction)
        else:
            tx_hash = fn.transact({"from": self._account})
        receipt = self._w3.eth.wait_for_transaction_receipt(tx_hash)
        index = self.total_trades() - 1
        return SettleReceipt(index=index, tx_hash=receipt["transactionHash"].hex())

    def position_of(self, party) -> Position:
        net_kwh, net_cents, trades = self._contract.functions.positionOf(party).call()
        return Position(net_kwh_milli=int(net_kwh), net_cents=int(net_cents), trades=int(trades))

    def total_trades(self) -> int:
        return int(self._contract.functions.totalTrades().call())
