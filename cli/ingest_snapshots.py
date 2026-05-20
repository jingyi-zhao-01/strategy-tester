"""Script to ingest option snapshots (prices, Greeks, implied volatility) for active contracts."""

from microservices.snapshot_ingestor.service import run


def main():
    """Ingest option snapshots (market data) for all active option contracts."""
    run()


if __name__ == "__main__":
    main()
