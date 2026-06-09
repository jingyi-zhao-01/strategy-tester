import logging
from collections.abc import AsyncGenerator
from importlib import import_module
from typing import TYPE_CHECKING

from microservices.shared.decorator import (
    CONCURRENCY_LIMIT,
    OPTION_BATCH_RETRIEVAL_SIZE,
    bounded_db_connection,
    bounded_db_connection_asyncgen,
)
from microservices.shared.observability import start_span_sync

if TYPE_CHECKING:  # pragma: no cover
    from prisma.models import Options  # type: ignore


logger = logging.getLogger(__name__)


class OptionRetriever:
    def __init__(self, concurrency_limit=CONCURRENCY_LIMIT, batch_size=OPTION_BATCH_RETRIEVAL_SIZE):
        self._ingest_time = None
        self.concurrency_limit = concurrency_limit
        self.skip_expired = True
        self.batch_size = batch_size

    def with_ingest_time(self, ingest_time) -> "OptionRetriever":
        self._ingest_time = ingest_time
        return self

    @property
    def ingest_time(self):
        if self._ingest_time is None:
            raise ValueError("OptionRetriever must be bound to an ingest time")
        return self._ingest_time

    @bounded_db_connection
    async def retrieve_all(self) -> list["Options"]:
        try:
            options_model = import_module("prisma.models").Options  # type: ignore
            contracts = await options_model.prisma().find_many()
            logger.info(
                "Retrieved %s unexpired option contracts from the database.", len(contracts)
            )
            return contracts
        except Exception as e:
            logger.exception("Error fetching option contracts: %s", e)
            return []

    @bounded_db_connection_asyncgen
    async def stream_retrieve_active(
        self, *args, **kwargs
    ) -> AsyncGenerator[list["Options"], None]:
        try:
            options_model = import_module("prisma.models").Options  # type: ignore
            logger.info(
                "Starting active contract retrieval for ingest session: %s", self.ingest_time
            )
            offset = 0
            while True:
                with start_span_sync(
                    "retrieve_active_batch",
                    attributes={
                        "module": "NEON",
                        "batch.offset": offset,
                        "batch.size": self.batch_size,
                    },
                ):
                    batch = await options_model.prisma().find_many(
                        skip=offset,
                        take=self.batch_size,
                        where={"expiration_date": {"gte": self.ingest_time}},
                    )
                if not batch:
                    break
                logger.info("Retrieved batch at offset %s for session %s", offset, self.ingest_time)
                yield batch
                offset += len(batch)
        except Exception as e:
            logger.exception("Error streaming option contracts: %s", e)
            return


__all__ = ["OptionRetriever"]
