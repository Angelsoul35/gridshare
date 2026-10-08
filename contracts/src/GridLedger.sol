// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title GridLedger
/// @author Angelo David Padilla Romero
/// @notice Settlement ledger for a peer-to-peer energy market.
/// @dev The off-chain market clears buyers and sellers each hour and asks the
///      operator to settle each trade here. The ledger records every trade and
///      keeps a running position per party: net energy (in milli-kWh) and net
///      money (in cents). Houses are identified by a bytes32 id (a hash of the
///      house name), so no personal data reaches the chain. Only the operator
///      can settle, which models the market clearinghouse.
contract GridLedger {
    struct Position {
        int256 netKwhMilli; // + received energy, - delivered energy (milli-kWh)
        int256 netCents; // + earned, - paid (cents)
        uint256 trades;
    }

    address public operator;
    uint256 public totalTrades;
    mapping(bytes32 => Position) private _positions;

    event TradeSettled(
        uint256 indexed index,
        bytes32 indexed buyer,
        bytes32 indexed seller,
        uint256 kWhMilli,
        uint256 priceCents,
        uint256 hour
    );
    event OperatorTransferred(address indexed previousOperator, address indexed newOperator);

    error NotOperator();
    error ZeroParty();
    error SameParty();
    error ZeroEnergy();

    modifier onlyOperator() {
        if (msg.sender != operator) revert NotOperator();
        _;
    }

    constructor() {
        operator = msg.sender;
        emit OperatorTransferred(address(0), msg.sender);
    }

    function transferOperator(address newOperator) external onlyOperator {
        if (newOperator == address(0)) revert ZeroParty();
        address previous = operator;
        operator = newOperator;
        emit OperatorTransferred(previous, newOperator);
    }

    /// @notice Settle one cleared trade between a buyer and a seller.
    /// @param kWhMilli energy traded, in milli-kWh (1 kWh = 1000).
    /// @param priceCents clearing price in cents per kWh.
    /// @return index the index of the settled trade.
    function settle(
        bytes32 buyer,
        bytes32 seller,
        uint256 kWhMilli,
        uint256 priceCents,
        uint256 hour
    ) external onlyOperator returns (uint256 index) {
        if (buyer == bytes32(0) || seller == bytes32(0)) revert ZeroParty();
        if (buyer == seller) revert SameParty();
        if (kWhMilli == 0) revert ZeroEnergy();

        uint256 cents = (kWhMilli * priceCents) / 1000;

        Position storage s = _positions[seller];
        s.netKwhMilli -= int256(kWhMilli);
        s.netCents += int256(cents);
        s.trades += 1;

        Position storage b = _positions[buyer];
        b.netKwhMilli += int256(kWhMilli);
        b.netCents -= int256(cents);
        b.trades += 1;

        index = totalTrades;
        totalTrades += 1;

        emit TradeSettled(index, buyer, seller, kWhMilli, priceCents, hour);
    }

    function positionOf(bytes32 party)
        external
        view
        returns (int256 netKwhMilli, int256 netCents, uint256 trades)
    {
        Position memory p = _positions[party];
        return (p.netKwhMilli, p.netCents, p.trades);
    }
}
