"""Script to ingest option contracts from Polygon API."""

import asyncio
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables BEFORE configuring logging
# Resolve the project root explicitly so systemd WorkingDirectory doesn't matter.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_ENV_PATH = _PROJECT_ROOT / ".env.options"
load_dotenv(dotenv_path=_ENV_PATH)

# noinspection PyUnresolvedReference
from cli.targets import TARGETS  # noqa: E402
from lib.observability import Log, configure_logging  # noqa: E402
from options.ingestor import OptionIngestor  # noqa: E402
from options.models import OptionIngestParams  # noqa: E402
from options.retriever import OptionRetriever  # noqa: E402

# Configure logging with OTEL enabled
configure_logging(
    service_name="option-ingestor",
    enable_otel=True,
)


def main():
    """Ingest option contracts from Polygon API into the database."""
    retriever = OptionRetriever()
    ingestor = OptionIngestor(option_retriever=retriever)
    underlying_assets = [OptionIngestParams(asset[0], asset[1], asset[2]) for asset in TARGETS]

    try:
        Log.info("-----------Starting option contracts ingestion...")
        asyncio.run(ingestor.ingest_options(underlying_assets=underlying_assets))
        Log.info("Option contracts ingestion completed successfully")
    except Exception as e:
        Log.error(f"Error during option contracts ingestion: {e}")
        raise


if __name__ == "__main__":
    main()
