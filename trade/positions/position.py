
"""Individual position state."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Position:
    """Individual position state."""

    symbol: str
    quantity: int
    entry_price: float
    current_price: Optional[float] = None
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0

    def get_value(self) -> float:
        """Get current position value."""
        if self.current_price is None:
            return self.quantity * self.entry_price
        return self.quantity * self.current_price

    def get_cost(self) -> float:
        """Get position cost."""
        return self.quantity * self.entry_price

    def update_unrealized_pnl(self):
        """Update unrealized P&L."""
        if self.current_price is not None:
            self.unrealized_pnl = (self.current_price - self.entry_price) * self.quantity

    def close(self, exit_price: float) -> float:
        """Close position and return realized P&L."""
        self.realized_pnl = (exit_price - self.entry_price) * self.quantity
        return self.realized_pnl


__all__ = ["Position"]
