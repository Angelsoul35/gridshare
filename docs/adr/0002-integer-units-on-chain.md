# ADR 0002: Store energy and money as integers on-chain

## Status

Accepted.

## Context

The ledger keeps a running position per house: how much energy it has given or
received and how much money it has earned or paid. The EVM has no
floating-point type, and even off-chain, floats accumulate rounding error. If
two parties computed positions slightly differently, they would disagree about
who owes what — exactly the problem the shared ledger is meant to solve.

Energy in the simulation is in kWh (fractional) and prices are in cents per kWh
(also fractional after averaging). We need a unit that is exact, that the EVM
can store, and that does not lose meaningful precision.

## Decision

Store energy as integer **milli-kWh** (1 kWh = 1000 milli-kWh) and money as
integer **cents**. The contract settles `cents = (kWhMilli * priceCents) / 1000`
using integer arithmetic. Positions are signed integers: positive energy means
received, negative means delivered; positive money means earned, negative means
paid.

The Python side rounds to these integer units at the boundary, just before it
calls `settle`, so the on-chain and off-chain views agree exactly.

## Consequences

- **Exact, reproducible accounting.** Every party computes the same position
  from the same trades. There is no float drift and no disagreement.
- **EVM-friendly.** Integers are the EVM's native type; no fixed-point library
  is needed.
- **Enough precision.** Milli-kWh (0.001 kWh) and cents are finer than any
  metering or billing decision in this domain.
- **Trade-off.** Rounding happens at the boundary, so a trade of, say, 2.4567
  kWh is recorded as 2456 milli-kWh. The lost fraction is negligible and the
  rounding rule is explicit and tested.
- The integer `cents = kWhMilli * priceCents / 1000` division truncates, which
  is deterministic and identical in Solidity and in the Python fake, so the two
  implementations match exactly.
