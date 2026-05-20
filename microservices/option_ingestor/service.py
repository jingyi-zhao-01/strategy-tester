"""Option ingestion service entrypoint."""

import asyncio

from lib.observability import Log, configure_logging
from microservices.config import (
    get_option_runtime_config,
    get_option_targets_from_env,
    get_retriever_config,
    load_env,
)
from microservices.option_ingestor.ingestor import OptionIngestor
from microservices.option_ingestor.retriever import OptionRetriever


def run() -> None:
    """Run option contracts ingestion as an isolated service."""
    load_env()
    runtime_config = get_option_runtime_config()
    retriever_config = get_retriever_config()

    configure_logging(
        service_name=runtime_config.service_name,
        enable_otel=runtime_config.enable_otel,
    )

    retriever = OptionRetriever(
        concurrency_limit=retriever_config.concurrency_limit,
        batch_size=retriever_config.batch_size,
    )
    ingestor = OptionIngestor(option_retriever=retriever)
    targets = get_option_targets_from_env()

    Log.info("-----------Starting option contracts ingestion...")
    asyncio.run(ingestor.ingest_options(underlying_assets=targets))
    Log.info("Option contracts ingestion completed successfully")
