"""Ingestor for option contracts."""

import asyncio
import logging
import os
from importlib import import_module

from microservices.option_ingestor.api import Fetcher
from microservices.option_ingestor.retriever import OptionRetriever
from microservices.shared.decorator import (
    DATA_BASE_CONCURRENCY_LIMIT,
    bounded_async_sem,
    bounded_db_connection,
    traced_span_async,
)
from microservices.shared.errors import is_retryable_db_error
from microservices.shared.models import OptionIngestParams, OptionsContract
from microservices.shared.util import get_current_datetime, option_expiration_date_to_datetime
from prisma.models import Options

logger = logging.getLogger(__name__)
DB_RETRY_MAX_ATTEMPTS = int(os.getenv("INGEST_DB_RETRY_MAX_ATTEMPTS", "3"))
DB_RETRY_BASE_DELAY_SECONDS = float(os.getenv("INGEST_DB_RETRY_BASE_DELAY_SECONDS", "0.5"))
DB_WRITE_BATCH_SIZE = int(os.getenv("INGEST_DB_WRITE_BATCH_SIZE", "25"))


class OptionIngestor:
    """Base class for option contract ingestion operations."""

    def __init__(self, option_retriever=None):
        self.ingest_time = get_current_datetime()

        if option_retriever is None:
            raise ValueError("option_retriever must be provided")

        self.option_retriever: OptionRetriever = option_retriever.with_ingest_time(self.ingest_time)

    @bounded_db_connection
    @traced_span_async(name="ingest_options", attributes={"module": "ingestor"})
    async def ingest_options(self, underlying_assets: list[OptionIngestParams]):
        """Ingest option contracts from the API and store them in the database."""
        for target in underlying_assets:
            underlying_asset = target.underlying_asset
            core = Fetcher(underlying_asset)
            calls = core.get_call_contracts()
            puts = core.get_put_contracts()

            contracts = calls + puts
            logger.info("Total contracts found for %s: %s", underlying_asset, len(contracts))
            if not contracts:
                logger.warning("No UnExpired contracts found for %s", underlying_asset)
                continue

            total_batches = 0
            for total_batches, contracts_batch in enumerate(
                _iter_contract_batches(contracts, DB_WRITE_BATCH_SIZE),
                start=1,
            ):
                logger.info(
                    "Processing contract batch %s for %s with %s contracts",
                    total_batches,
                    underlying_asset,
                    len(contracts_batch),
                )
                await asyncio.gather(
                    *[self._upsert_option_contract(contract) for contract in contracts_batch]
                )
            logger.info("All contracts for %s processed successfully", underlying_asset)

    async def _retrieve_all_option_contracts(self) -> list["Options"]:
        """Retrieve all option contracts from the database."""
        try:
            options = import_module("prisma.models").Options  # type: ignore
            contracts = await options.prisma().find_many()
            logger.info("Retrieved %s option contracts from the database.", len(contracts))
            return contracts
        except Exception as e:
            logger.exception("Error fetching option contracts: %s", e)
            return []

    @bounded_async_sem(limit=DATA_BASE_CONCURRENCY_LIMIT)
    @traced_span_async(name="_upsert_option_contract", attributes={"module": "DB"})
    async def _upsert_option_contract(
        self,
        contract: OptionsContract,
        max_retries: int = DB_RETRY_MAX_ATTEMPTS,
        base_delay_seconds: float = DB_RETRY_BASE_DELAY_SECONDS,
    ) -> "Options":
        """Upsert a single option contract into the database."""
        expiration_dt = option_expiration_date_to_datetime(str(contract.expiration_date))
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(
                    "Upserting contract: %s, Strike: %s, Expiration: %s, Type: %s",
                    contract.ticker,
                    contract.strike_price,
                    expiration_dt,
                    contract.contract_type,
                )
                options = import_module("prisma.models").Options  # type: ignore
                return await options.prisma().upsert(
                    where={"ticker": str(contract.ticker)},
                    data={
                        "create": {
                            "ticker": str(contract.ticker),
                            "underlying_ticker": str(contract.underlying_ticker),
                            "strike_price": (
                                float(contract.strike_price)
                                if contract.strike_price is not None
                                else 0.0
                            ),
                            "expiration_date": expiration_dt,
                            "contract_type": "CALL" if contract.contract_type == "call" else "PUT",
                        },
                        "update": {
                            "underlying_ticker": str(contract.underlying_ticker),
                            "strike_price": (
                                float(contract.strike_price)
                                if contract.strike_price is not None
                                else 0.0
                            ),
                            "expiration_date": expiration_dt,
                            "contract_type": "CALL" if contract.contract_type == "call" else "PUT",
                        },
                    },
                )
            except Exception as e:
                logger.exception(
                    "Error upserting contract %s: %s (%s) attempt %s/%s",
                    contract.ticker,
                    e,
                    type(e).__name__,
                    attempt,
                    max_retries,
                )
                if not is_retryable_db_error(e) or attempt >= max_retries:
                    raise

                delay = base_delay_seconds * (2 ** (attempt - 1))
                logger.warning(
                    "Retrying contract %s after transient DB error in %.2fs",
                    contract.ticker,
                    delay,
                )
                await asyncio.sleep(delay)

        raise RuntimeError(f"Unreachable retry loop for contract {contract.ticker}")


def _iter_contract_batches(
    contracts: list[OptionsContract], batch_size: int
) -> list[list[OptionsContract]]:
    normalized_batch_size = max(1, batch_size)
    return [
        contracts[index : index + normalized_batch_size]
        for index in range(0, len(contracts), normalized_batch_size)
    ]


__all__ = ["OptionIngestor"]
