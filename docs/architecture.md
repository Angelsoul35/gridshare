# Architecture

GridShare simulates a local, hour-by-hour energy market for a neighbourhood and
settles each trade on an EVM ledger. This document describes the pieces, how
data flows through them, and the boundaries between them.

## The pieces

| Layer          | Module                         | Responsibility                                            |
| -------------- | ------------------------------ | --------------------------------------------------------- |
| Meters         | `gridshare/generate.py`        | Synthetic per-house hourly generation and consumption     |
| Forecast       | `gridshare/forecast.py`        | Predict each house's net energy for an hour of the day    |
| Market         | `gridshare/market.py`          | Uniform-price double auction between buyers and sellers   |
| Orchestration  | `gridshare/service.py`         | Build orders, clear the market, settle trades             |
| Ledger clients | `gridshare/chain/ledger.py`    | Talk to the contract (or an in-memory fake)               |
| Artifacts      | `gridshare/chain/artifacts.py` | Load the committed ABI + bytecode                          |
| Compiler       | `gridshare/chain/compile.py`   | Build the artifact from Solidity via `solc-js`            |
| Contract       | `contracts/src/GridLedger.sol` | Record trades and running positions on-chain              |
| HTTP API       | `gridshare/main.py`            | Expose the market over REST                               |
| CLI            | `gridshare/cli.py`             | End-to-end demo against an in-memory EVM                  |

## Data flow for one hour

```
┌──────────────┐   net = gen − cons   ┌──────────────┐
│  history     │ ───────────────────▶ │  orders      │
│ (synthetic)  │   per house, hour     │ bids + asks  │
└──────────────┘                       └──────┬───────┘
                                               │  clear_market(...)
                                               ▼
                                        ┌──────────────┐
                                        │ MarketResult │
                                        │ trades, price│
                                        └──────┬───────┘
                                               │  for each trade: settle(...)
                                               ▼
                                        ┌──────────────┐
                                        │  GridLedger  │
                                        │  positions   │
                                        └──────────────┘
```

1. `GridShareService` reads the simulated day's history and turns each house's
   net energy into an order. A deficit becomes a **bid** below the grid retail
   price; a surplus becomes an **ask** above the grid feed-in price. A small,
   deterministic per-house margin keeps the clearing price from always landing
   on the exact midpoint.
2. `clear_market` runs the double auction and returns the trades, the single
   clearing price, the peer-to-peer energy, the leftover grid import/export, and
   the savings for each side compared with trading only with the grid.
3. For each trade, the service calls `settle` on the ledger client with the
   buyer and seller ids, the energy in milli-kWh, the clearing price in cents,
   and the hour.

## Why milli-kWh and cents

The contract stores energy as integer **milli-kWh** (1 kWh = 1000) and money as
integer **cents**. The EVM has no floating-point numbers, and floats would make
positions drift and disagree between parties. Fixed integer units keep the
on-chain accounting exact and reproducible. The Python side rounds to these
units at the boundary before it settles.

## The ledger boundary

`LedgerClient` is a `Protocol` with two implementations:

- **`Web3LedgerClient`** talks to a deployed `GridLedger` over JSON-RPC. It
  signs and sends transactions when given a private key, or uses an unlocked
  node account otherwise (handy for an in-memory test node).
- **`InMemoryLedgerClient`** mirrors the contract's accounting in a dictionary,
  with the same guards (zero party, same party, zero energy).

Because both satisfy the same protocol, the service, the API, and the tests do
not care which one is behind them. This keeps the chain optional: the HTTP API
can run with no chain at all, and the contract tests still prove the real
contract behaves like the fake.

## Compilation strategy

The Solidity source is compiled by a pinned `solc-js` compiler invoked through
`node contracts/compile.js`. There is no native `solc` binary to install, so the
build is identical on a laptop and in CI. The resulting artifact (ABI +
bytecode) is committed under `contracts/artifacts/`, which lets the runtime and
the tests deploy the contract to any endpoint without running a compiler.

## Privacy

Houses are identified on-chain by a `bytes32` id, which is the keccak hash of
the house name. The chain records energy, money, and a trade count per id, but
never a name, a meter number, or any other personal data. The mapping from a
real identity to an id stays off-chain, under the operator's control.

## Boundaries and extension points

- **Forecast model.** `HourlyMeanForecaster` is a baseline. A stronger model
  (gradient boosting, a weather-aware model) can replace it behind the same
  `fit` / `forecast_net` / `mae` interface.
- **Market mechanism.** `clear_market` is a pure function. A different auction
  (pay-as-bid, a reserve price, grid constraints) can be dropped in without
  touching the service or the chain.
- **Settlement target.** Pointing `GS_CHAIN_RPC_URL` and `GS_CONTRACT_ADDRESS`
  at a live node is the only change needed to settle on a real chain.
