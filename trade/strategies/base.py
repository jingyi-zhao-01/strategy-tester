
"""Base strategy abstract class."""
from abc import ABC, abstractmethod


class BaseStrategy(ABC):
    """Abstract base class for trading strategies."""

    @abstractmethod
    def generate_signals(self, market_data):
        """Generate trading signals based on market data."""
        pass

    @abstractmethod
    def calculate_position_size(self, signal, portfolio_value):
        """Calculate position size based on signal and portfolio value."""
        pass

    @abstractmethod
    def should_exit(self, position, market_data):
        """Determine if a position should be exited."""
        pass


__all__ = ["BaseStrategy"]
