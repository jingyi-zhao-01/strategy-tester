"""Option ingestion service entrypoint."""

import asyncio
import logging

from microservices.config import (
    get_option_runtime_config,
    get_option_targets_from_env,
    get_retriever_config,
    load_env,
)
from microservices.option_ingestor.ingestor import OptionIngestor
from microservices.option_ingestor.retriever import OptionRetriever
from microservices.shared import connect_db, disconnect_db
from microservices.shared.observability import (
    configure_service_logger,
    initialize_tracing,
    shutdown_tracing,
)


def _configure_logging(service_name: str) -> None:
    configure_service_logger(service_name)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger(service_name)


logger = logging.getLogger(__name__)


async def _run_job(ingestor: OptionIngestor, targets) -> None:
    await connect_db()
    try:
        await ingestor.ingest_options(underlying_assets=targets)
    finally:
        await disconnect_db()


def run() -> None:
    """Run option contracts ingestion as an isolated service."""
    load_env()
    runtime_config = get_option_runtime_config()
    retriever_config = get_retriever_config()

    initialize_tracing(runtime_config.service_name)
    _configure_logging(service_name=runtime_config.service_name)

    retriever = OptionRetriever(
        concurrency_limit=retriever_config.concurrency_limit,
        batch_size=retriever_config.batch_size,
    )
    ingestor = OptionIngestor(option_retriever=retriever)
    targets = get_option_targets_from_env()

    try:
        logger.info("-----------Starting option contracts ingestion...")
        asyncio.run(_run_job(ingestor=ingestor, targets=targets))
        logger.info("Option contracts ingestion completed successfully")
    finally:
        shutdown_tracing()
