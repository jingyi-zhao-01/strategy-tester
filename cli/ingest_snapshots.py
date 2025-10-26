"""Script to ingest option snapshots (prices, Greeks, implied volatility) for active contracts."""

import asyncio
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables BEFORE configuring logging
# Resolve the project root explicitly so systemd WorkingDirectory doesn't matter.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_ENV_PATH = _PROJECT_ROOT / ".env.snapshots"
load_dotenv(dotenv_path=_ENV_PATH)

# noinspection PyUnresolvedReference
from lib.observability import Log, configure_logging  # noqa: E402
from options.ingestor import OptionSnapshotsIngestor  # noqa: E402
from options.retriever import OptionRetriever  # noqa: E402

# Configure logging with OTEL enabled
configure_logging(
    service_name="snapshot-ingestor",
    enable_otel=True,
)


def main():
    """Ingest option snapshots (market data) for all active option contracts."""
    retriever = OptionRetriever()
    ingestor = OptionSnapshotsIngestor(option_retriever=retriever)

    try:
        Log.info("-----------Starting option snapshots ingestion...")
        asyncio.run(ingestor.ingest_option_snapshots())
        Log.info("Option snapshots ingestion completed successfully")
    except Exception as e:
        Log.error(f"Error during option snapshots ingestion: {e}")
        raise


if __name__ == "__main__":
    main()
