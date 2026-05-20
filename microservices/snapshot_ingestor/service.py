"""Option snapshot ingestion service entrypoint."""

import asyncio

from lib.observability import Log, configure_logging
from microservices.config import get_retriever_config, get_snapshot_runtime_config, load_env
from microservices.option_ingestor.retriever import OptionRetriever
from microservices.snapshot_ingestor.ingestor import OptionSnapshotsIngestor


def run() -> None:
    """Run option snapshot ingestion as an isolated service."""
    load_env()
    runtime_config = get_snapshot_runtime_config()
    retriever_config = get_retriever_config()

    configure_logging(
        service_name=runtime_config.service_name,
        enable_otel=runtime_config.enable_otel,
    )

    retriever = OptionRetriever(
        concurrency_limit=retriever_config.concurrency_limit,
        batch_size=retriever_config.batch_size,
    )
    ingestor = OptionSnapshotsIngestor(option_retriever=retriever)

    Log.info("-----------Starting option snapshots ingestion...")
    asyncio.run(ingestor.ingest_option_snapshots())
    Log.info("Option snapshots ingestion completed successfully")
