import asyncio

from lib import Log
from options.api.options import Core, fetch_snapshots_batch, get_contract_within_price_range

from .models import OptionIngestParams
from .operations import (
    db,
    get_all_option_contracts,
    process_option_contracts,
    process_option_snapshot,
)

# TODO: Open Interest vs expiration date vs strike price

CONCURRENCY_LIMIT = 500


class OptionIngestor:
    def __init__(self, concurrency_limit=CONCURRENCY_LIMIT):
        self.semaphore = asyncio.Semaphore(concurrency_limit)
        self.ingestTime = None

    async def ingest_options(self, underlying_assets: list[OptionIngestParams]):
        await db.connect()
        try:
            for target in underlying_assets:
                underlying_asset = target.underlying_asset
                price_range = target.price_range
                year_range = target.year_range
                core = Core(underlying_asset)
                calls = core.get_call_contracts()
                puts = core.get_put_contracts()

                contracts = calls + puts
                Log.info(f"Total contracts found for {underlying_asset}: {len(contracts)}")

                contracts_within_range = get_contract_within_price_range(
                    contracts, price_range, year_range
                )
                Log.info(
                    f"Contracts within price range for {underlying_asset}: "
                    f"{len(contracts_within_range)}"
                )

                await asyncio.gather(
                    *[
                        self._process_option_contracts_with_semaphore(contract)
                        for contract in contracts_within_range
                    ]
                )
                Log.info(f"All contracts for {underlying_asset} processed successfully")
        except Exception as e:
            Log.error(f"Error during options ingestion: {e}")
            raise e
        finally:
            await db.disconnect()

    async def ingest_option_snapshots(self):
        await db.connect()
        try:
            contracts = await get_all_option_contracts(db)
            Log.info(f"Existing Contracts in database: {len(contracts)}")

            snapshots = await fetch_snapshots_batch(contracts)

            await asyncio.gather(
                *[
                    self._process_option_snapshot_with_semaphore(contract, snapshot)
                    for contract, snapshot in zip(contracts, snapshots)
                ]
            )

            Log.info("All option snapshots processed successfully")

        except Exception as e:
            Log.error(f"Error during option snapshots ingestion: {e}")
            raise e
        finally:
            await db.disconnect()

    async def _process_option_contracts_with_semaphore(self, contract):
        async with self.semaphore:
            await process_option_contracts(db, contract)

    async def _process_option_snapshot_with_semaphore(self, contract, snapshot):
        async with self.semaphore:
            await process_option_snapshot(db, contract.ticker, snapshot)


if __name__ == "__main__":
    LIMIT = 5

    ASSET = "SE"
    LIMIT = 100
    PRICE_RANGE = (140, 200)
    YEAR_RANGE = (2025, 2025)

    UNDERLYING_ASSET = "NBIS"
    NBIS_PARAMS = (UNDERLYING_ASSET, (40, 70), (2025, 2025))

    ASSET = "HOOD"
    HOOD_PARAMS = (ASSET, (100, 150), (2025, 2025))

    ASSET = "FCX"
    FCX_PARAMS = (ASSET, (45, 50), (2025, 2025))
    ingestor = OptionIngestor()

    # asyncio.run(ingest_options(NBIS_PARAMS))
    asyncio.run(ingestor.ingest_option_snapshots())


__all__ = ["OptionIngestor"]
