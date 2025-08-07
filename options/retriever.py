# TODO: Isolate
from collections.abc import AsyncGenerator

from lib import Log
from options.config import (
    CONCURRENCY_LIMIT,
    OPTION_BATCH_RETRIEVAL_SIZE,
    bounded_db_connection,
)
from prisma.models import Options


class OptionRetriever:
    def __init__(self, concurrency_limit=CONCURRENCY_LIMIT):
        self._ingest_time = None  # No time initialization here - subscribes to ingestor's time
        self.concurrency_limit = concurrency_limit
        self.skip_expired = True

    def with_ingest_time(self, ingest_time) -> "OptionRetriever":
        self._ingest_time = ingest_time
        return self

    @property
    def ingest_time(self):
        if self._ingest_time is None:
            raise ValueError("OptionRetriever must be bound to an ingest time")
        return self._ingest_time

    @bounded_db_connection
    async def retrieve_all(self) -> list[Options]:
        try:
            contracts = await Options.prisma().find_many(
                # where={"expiration_date": {"gte": self.ingest_time}}
            )
            Log.info(f"Retrieved {len(contracts)} unexpired option contracts from the database.")
            return contracts
        except Exception as e:
            Log.error(f"Error fetching option contracts: {e}")
            return []

    # bound iterator with db
    # @bounded_db
    async def stream_retrieve(self) -> AsyncGenerator[list[Options], None]:
        try:
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
