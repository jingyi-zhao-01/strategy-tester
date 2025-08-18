# TODO: Isolate
from collections.abc import AsyncGenerator

from lib import Log
from options.decorator import (
    CONCURRENCY_LIMIT,
    OPTION_BATCH_RETRIEVAL_SIZE,
    bounded_db_connection,
    traced_span_asyncgen,
)
from typing import TYPE_CHECKING
from importlib import import_module

if TYPE_CHECKING:  # pragma: no cover
    from prisma.models import Options  # type: ignore


class OptionRetriever:
    def __init__(self, concurrency_limit=CONCURRENCY_LIMIT, batch_size=OPTION_BATCH_RETRIEVAL_SIZE):
        self._ingest_time = None  # No time initialization here - subscribes to ingestor's time
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
            Options = import_module("prisma.models").Options  # type: ignore
            contracts = await Options.prisma().find_many()
            Log.info(f"Retrieved {len(contracts)} unexpired option contracts from the database.")
            return contracts
        except Exception as e:
            Log.error(f"Error fetching option contracts: {e}")
            return []

    # #TODO: bound iterator with db
    # @bounded_db
    @traced_span_asyncgen(name="stream_retrieve_active", attributes={"module": "NEON"})
    async def stream_retrieve_active(self, *args, **kwargs) -> AsyncGenerator[list["Options"], None]:
        try:
            Options = import_module("prisma.models").Options  # type: ignore
            Log.info(f"Starting active contract retrieval for ingest session: {self.ingest_time}")
            offset = 0
            while True:
                batch = await Options.prisma().find_many(
                    skip=offset,
                    take=OPTION_BATCH_RETRIEVAL_SIZE,
                    where={"expiration_date": {"gte": self.ingest_time}},
                )
                if not batch:
                    break
                Log.info(f"Retrieved batch at offset {offset} for session {self.ingest_time}")
                yield batch
                offset += len(batch)
        except Exception as e:
            Log.error(f"Error streaming option contracts: {e}")
            return


__all__ = [
    "OptionRetriever",
]
