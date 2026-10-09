# ADR 0004: Compile with solc-js and commit the artifact

## Status

Accepted.

## Context

The project needs to compile a Solidity contract and deploy it from Python. The
usual options are:

- a native `solc` binary, installed per platform;
- a downloaded `solc` at runtime (for example via `py-solc-x`);
- the JavaScript compiler `solc-js`, pinned as an npm dependency.

A native binary is another platform-specific tool to install and keep in step
between a laptop and CI. Downloading a compiler at runtime needs network access
at an awkward time and makes builds depend on an external host being reachable.

We also want the runtime and the tests to be able to deploy the contract
**without** any compiler present, so that running the app or the test suite is
not blocked by a toolchain.

## Decision

Compile with **`solc-js`**, pinned in `contracts/package.json` and invoked
through `node contracts/compile.js` (wrapped by `python -m gridshare.chain.compile`
and `make compile`). **Commit** the resulting artifact (ABI + bytecode) under
`contracts/artifacts/GridLedger.json`.

At runtime, `artifacts.py` loads the committed JSON; it never shells out to a
compiler.

## Consequences

- **Identical builds everywhere.** The same pinned compiler version runs on a
  laptop and in CI, through Node, with no native toolchain.
- **No compiler needed to run or test.** The committed artifact lets the runtime
  and the tests deploy the contract to any JSON-RPC endpoint directly.
- **Reviewable output.** The artifact is in version control, so a change to the
  bytecode shows up in a diff and can be reviewed.
- **Trade-off.** The committed artifact must be regenerated with `make compile`
  whenever the contract changes, and the diff must be committed. This is a small,
  explicit step and keeps the source and the artifact consistent with each other.
