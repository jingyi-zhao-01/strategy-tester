"""Ingestor for option contracts."""

import asyncio
import traceback

# Avoid hard dependency bindings to enable unit tests to monkeypatch via module paths
from importlib import import_module

from lib.observability import Log
from options.util import (
    get_current_datetime,
    option_expiration_date_to_datetime,
)
from prisma.models import Options

from ..decorator import (
    DATA_BASE_CONCURRENCY_LIMIT,
    bounded_async_sem,
    bounded_db_connection,
    traced_span_async,
)
from ..models import OptionIngestParams, OptionsContract
from ..retriever import OptionRetriever


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
            fetcher = import_module("options.api.options").Fetcher  # type: ignore
            core = fetcher(underlying_asset)
            calls = core.get_call_contracts()
            puts = core.get_put_contracts()

            contracts = calls + puts
            Log.info(f"Total contracts found for {underlying_asset}: {len(contracts)}")
            if not contracts:
                Log.warn(f"No UnExpired contracts found for {underlying_asset}")
                continue

            await asyncio.gather(
                *[self._upsert_option_contract(contract) for contract in contracts]
            )
            Log.info(f"All contracts for {underlying_asset} processed successfully")

    async def _retrieve_all_option_contracts(self) -> list["Options"]:
        """Retrieve all option contracts from the database."""
        try:
            options = import_module("prisma.models").Options  # type: ignore
            contracts = await options.prisma().find_many()
            Log.info(f"Retrieved {len(contracts)} option contracts from the database.")
            return contracts
        except Exception as e:
            Log.error(f"Error fetching option contracts: {e}")
            return []

    @bounded_async_sem(limit=DATA_BASE_CONCURRENCY_LIMIT)
    @traced_span_async(name="_upsert_option_contract", attributes={"module": "DB"})
    async def _upsert_option_contract(self, contract: OptionsContract) -> "Options":
        """Upsert a single option contract into the database."""
        expiration_dt = option_expiration_date_to_datetime(str(contract.expiration_date))
        try:
            Log.info(
                f"Upserting contract: {contract.ticker}, "
                f"Strike: {contract.strike_price}, "
                f"Expiration: {expiration_dt}, "
                f"Type: {contract.contract_type}"
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
            Log.error(f"Error upserting contract {contract.ticker}: {e} ({type(e).__name__})")
            Log.error(traceback.format_exc())
            raise


__all__ = ["OptionIngestor"]
