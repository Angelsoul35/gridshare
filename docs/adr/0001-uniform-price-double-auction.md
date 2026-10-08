# ADR 0001: A uniform-price double auction for the local market

## Status

Accepted.

## Context

Each hour, some houses have surplus solar and some have a deficit. We need a
rule that decides who trades with whom and at what price. The rule has to be
fair, easy to explain to a non-expert, and good for both sides compared with
trading only with the grid, where selling pays the low feed-in price and buying
costs the high retail price.

Several mechanisms were possible:

- **Pay-as-bid.** Each pair settles at its own price. Simple to run but it
  rewards guessing the right bid and can feel unfair when neighbours pay very
  different prices for the same energy in the same hour.
- **A fixed split** (for example, always the midpoint of the grid buy and sell
  prices). Very simple, but it ignores how much supply and demand there actually
  is in a given hour.
- **A uniform-price double auction.** Sort buyers by bid and sellers by ask,
  match while a buyer still beats a seller, and settle all matched energy at one
  clearing price.

## Decision

Use a **uniform-price double auction**. Buyers are sorted by bid (high to low),
sellers by ask (low to high), and they are matched while the current buyer's bid
is at least the current seller's ask. All matched energy settles at a single
clearing price: the midpoint of the last matched pair.

## Consequences

- **Fair within the hour.** Everyone who trades in an hour pays or receives the
  same price, which is easy to defend to participants.
- **Both sides win.** The clearing price sits between the grid feed-in and
  retail prices, so the seller earns more than the grid would pay and the buyer
  pays less than the grid would charge. We report these savings explicitly.
- **A single, readable number.** One clearing price per hour is easy to log,
  audit, and settle on-chain.
- **Trade-off.** A uniform price can leave a small amount of "almost-matched"
  energy untraded at the margin; that energy simply trades with the grid. This
  is acceptable and keeps the mechanism simple.
- `clear_market` stays a pure function, so it is trivial to test and to swap for
  a different mechanism later.
