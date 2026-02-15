
"""Portfolio tracking."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Portfolio:
    """Portfolio tracking."""

    cash: float = 0.0
    positions: dict = field(default_factory=dict)
    initial_value: float = 0.0

    def get_total_value(self, current_prices: dict[str, float]) -> float:
        """Calculate total portfolio value."""
        positions_value = sum(
            pos.quantity * current_prices.get(pos.symbol, 0)
            for pos in self.positions.values()
        )
        return self.cash + positions_value

    def get_position(self, symbol: str):
        """Get position for a symbol."""
        return self.positions.get(symbol)

    def add_position(self, symbol: str, quantity: int, entry_price: float):
        """Add or update a position."""
        if symbol in self.positions:
            pos = self.positions[symbol]
            total_cost = pos.quantity * pos.entry_price + quantity * entry_price
            pos.quantity += quantity
            pos.entry_price = total_cost / pos.quantity
        else:
            from trade.positions.position import Position
            self.positions[symbol] = Position(symbol, quantity, entry_price)

    def remove_position(self, symbol: str, quantity: int):
        """Remove quantity from a position."""
        if symbol in self.positions:
            pos = self.positions[symbol]
            pos.quantity -= quantity
            if pos.quantity <= 0:
                del self.positions[symbol]


__all__ = ["Portfolio"]
