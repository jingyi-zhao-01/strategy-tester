
"""Signal generation logic."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SignalType(Enum):
    """Types of trading signals."""

    ENTRY = "entry"
    EXIT = "exit"
    ADJUST = "adjust"


class SignalDirection(Enum):
    """Signal direction."""

    LONG = "long"
    SHORT = "short"
    CLOSE = "close"


@dataclass
class Signal:
    """Trading signal representation."""

    symbol: str
    signal_type: SignalType
    direction: SignalDirection
    strength: float  # 0.0 to 1.0
    timestamp: str
    metadata: Optional[dict] = None


class SignalGenerator:
    """Generates trading signals based on market data and strategies."""

    def __init__(self, strategy):
        self.strategy = strategy

    def generate_signals(self, market_data: dict) -> list[Signal]:
        """Generate trading signals based on market data."""
        return self.strategy.generate_signals(market_data)

    def filter_signals(self, signals: list[Signal], min_strength: float = 0.5) -> list[Signal]:
        """Filter signals by minimum strength."""
        return [s for s in signals if s.strength >= min_strength]


__all__ = ["Signal", "SignalType", "SignalDirection", "SignalGenerator"]
