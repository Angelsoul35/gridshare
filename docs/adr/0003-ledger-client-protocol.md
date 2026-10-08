# ADR 0003: A ledger-client protocol with an in-memory fake

## Status

Accepted.

## Context

The market needs to settle trades on the `GridLedger` contract. But we also
want to:

- run the HTTP API with no chain at all, for demos and local work;
- test the market logic without spinning up a node;
- prove that the real contract behaves the way the rest of the system expects.

Talking to a chain directly from the service would couple the market to web3,
make tests slow and flaky, and make a chainless mode awkward.

## Decision

Define a `LedgerClient` `Protocol` with a small surface — `address`, `settle`,
`position_of`, `total_trades` — and provide two implementations:

- **`Web3LedgerClient`**, which talks to a deployed contract over JSON-RPC and
  signs transactions when given a private key.
- **`InMemoryLedgerClient`**, a dictionary-backed fake that mirrors the
  contract's accounting and its guards (zero party, same party, zero energy).

The service, the API, and the CLI depend only on the protocol, never on a
concrete client.

## Consequences

- **Chain is optional.** The API runs with the in-memory fake when no chain is
  configured, and with a real client when one is.
- **Fast tests.** Market and service tests use the fake and need no node. A
  separate set of `chain`-marked tests deploys the real contract to an in-memory
  PyEVM node.
- **The fake stays honest.** A dedicated test settles the same trade on both the
  real contract and the fake and asserts their positions match, so the fake
  cannot drift away from the contract's behaviour.
- **Trade-off.** Two implementations must be kept in step. The equivalence test
  is what keeps that cost low and catches any divergence early.
