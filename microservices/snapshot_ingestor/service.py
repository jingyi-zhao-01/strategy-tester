"""Option snapshot ingestion service entrypoint."""

import asyncio
import logging

from microservices.config import get_retriever_config, get_snapshot_runtime_config, load_env
from microservices.option_ingestor.retriever import OptionRetriever
from microservices.shared.observability import configure_service_logger, initialize_tracing
from microservices.snapshot_ingestor.ingestor import OptionSnapshotsIngestor


def _configure_logging(service_name: str) -> None:
    configure_service_logger(service_name)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger(service_name)


logger = logging.getLogger(__name__)


def run() -> None:
    """Run option snapshot ingestion as an isolated service."""
    load_env()
    runtime_config = get_snapshot_runtime_config()
    retriever_config = get_retriever_config()

    initialize_tracing(runtime_config.service_name)
    _configure_logging(service_name=runtime_config.service_name)

    retriever = OptionRetriever(
        concurrency_limit=retriever_config.concurrency_limit,
        batch_size=retriever_config.batch_size,
    )
    ingestor = OptionSnapshotsIngestor(option_retriever=retriever)

    logger.info("-----------Starting option snapshots ingestion...")
    asyncio.run(ingestor.ingest_option_snapshots())
    logger.info("Option snapshots ingestion completed successfully")
