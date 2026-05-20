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


def _configure_logging(service_name: str) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger(service_name)


logger = logging.getLogger(__name__)


def run() -> None:
    """Run option contracts ingestion as an isolated service."""
    load_env()
    runtime_config = get_option_runtime_config()
    retriever_config = get_retriever_config()

    _configure_logging(service_name=runtime_config.service_name)

    retriever = OptionRetriever(
        concurrency_limit=retriever_config.concurrency_limit,
        batch_size=retriever_config.batch_size,
    )
    ingestor = OptionIngestor(option_retriever=retriever)
    targets = get_option_targets_from_env()

    logger.info("-----------Starting option contracts ingestion...")
    asyncio.run(ingestor.ingest_options(underlying_assets=targets))
    logger.info("Option contracts ingestion completed successfully")
