
"""Broker interface for trade execution (TradeStation)."""


class Broker:
    """Abstract broker interface for order execution."""

    def __init__(self, api_key: str, secret: str, account_id: str):
        self.api_key = api_key
        self.secret = secret
        self.account_id = account_id

    async def place_order(self, order):
        """Place an order with the broker."""
        raise NotImplementedError

    async def cancel_order(self, order_id: str):
        """Cancel an existing order."""
        raise NotImplementedError

    async def get_positions(self):
        """Get current positions."""
        raise NotImplementedError

    async def get_account_info(self):
        """Get account information."""
        raise NotImplementedError


class TradeStationBroker(Broker):
    """TradeStation broker implementation."""

    async def place_order(self, order):
        """Place an order with TradeStation."""
        # Implementation placeholder
        pass

    async def cancel_order(self, order_id: str):
        """Cancel an existing order with TradeStation."""
        # Implementation placeholder
        pass

    async def get_positions(self):
        """Get current positions from TradeStation."""
        # Implementation placeholder
        pass

    async def get_account_info(self):
        """Get account information from TradeStation."""
        # Implementation placeholder
        pass


__all__ = ["Broker", "TradeStationBroker"]
