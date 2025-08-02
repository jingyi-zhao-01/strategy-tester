import asyncio
from collections.abc import AsyncGenerator

from lib import Log
from options.api.options import Core, fetch_snapshots_batch, get_contract_within_price_range
from options.util import (
    format_snapshot,
    get_current_datetime,
    ns_to_datetime,
    option_expiration_date_to_datetime,
)
from prisma import Prisma
from prisma.errors import UniqueViolationError
from prisma.models import Options, OptionSnapshot

from .models import OptionContractSnapshot, OptionIngestParams, OptionsContract

db = Prisma(auto_register=True)

# TODO: Open Interest vs expiration date vs strike price

CONCURRENCY_LIMIT = 250
OPTION_BATCH_RETRIEVAL_SIZE = 500


# TODO: what is Semaphore
# what is functional programming in python


def with_semaphore(semaphore):
    def wrapper(coro):
        async def inner(*args, **kwargs):
            async with semaphore:
                return await coro(*args, **kwargs)

        return inner

    return wrapper


class OptionTickerNeverActiveError(Exception):
    """Base class for other exceptions."""

    pass


class OptionRetriever:
    def __init__(self, concurrency_limit=CONCURRENCY_LIMIT):
        # self.semaphore = asyncio.Semaphore(concurrency_limit)
        pass

    # Deprecated:
    async def retrieve(self) -> list[Options]:
        try:
            contracts = await Options.prisma().find_many()
            Log.info(f"Retrieved {len(contracts)} option contracts from the database.")
            return contracts
        except Exception as e:
            Log.error(f"Error fetching option contracts: {e}")
            return []
        finally:
            await db.disconnect()

    async def stream_retrieve(self) -> AsyncGenerator[list[Options], None]:
        try:
            offset = 0
            while True:
                batch = await Options.prisma().find_many(
                    skip=offset, take=OPTION_BATCH_RETRIEVAL_SIZE
                )
                if not batch:
                    break
                yield batch
                offset += len(batch)
        except Exception as e:
            Log.error(f"Error streaming option contracts: {e}")
            return


option_retriever = OptionRetriever()


class OptionIngestor:
    def __init__(self, concurrency_limit=CONCURRENCY_LIMIT):
        self.concurrency_limit = concurrency_limit
        self.ingest_time = get_current_datetime()

    async def ingest_options(self, underlying_assets: list[OptionIngestParams]):
        semaphore = asyncio.Semaphore(self.concurrency_limit)
        process_with_sema = with_semaphore(semaphore)(self._upsert_option_contract)
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
                if not contracts:
                    Log.warn(f"No UnExpired contracts found for {underlying_asset}")
                    continue

                contracts_within_range = get_contract_within_price_range(
                    contracts, price_range, year_range
                )
                Log.info(
                    f"Contracts within price range for {underlying_asset}: "
                    f"{len(contracts_within_range)}"
                )

                await asyncio.gather(
                    *[process_with_sema(contract) for contract in contracts_within_range]
                )
                Log.info(f"All contracts for {underlying_asset} processed successfully")
        except Exception as e:
            Log.error(f"Error during options ingestion: {e}")
            raise e
        finally:
            await db.disconnect()

    async def ingest_option_snapshots(self):
        semaphore = asyncio.Semaphore(self.concurrency_limit)
        process_with_sema = with_semaphore(semaphore)(self._insert_option_snapshot)
        await db.connect()
        try:
            total_contracts = 0
            async for contracts_batch in option_retriever.stream_retrieve():
                Log.info(f"Processing batch of {len(contracts_batch)} contracts...")
                total_contracts += len(contracts_batch)
                snapshots = await fetch_snapshots_batch(contracts_batch)
                await asyncio.gather(
                    *[
                        process_with_sema(contract.ticker, snapshot)
                        for contract, snapshot in zip(contracts_batch, snapshots)
                    ]
                )
            Log.info(
                f"All option snapshots processed successfully. "
                f"Total contracts processed: {total_contracts}"
            )
        except Exception as e:
            Log.error(f"Error during option snapshots ingestion: {e}")
            raise e
        finally:
            await db.disconnect()

    async def _upsert_option_contract(self, contract: OptionsContract) -> Options:
        expiration_dt = option_expiration_date_to_datetime(contract.expiration_date)
        Log.info(
            f"Upserting contract: {contract.ticker}, "
            f"Strike: {contract.strike_price}, "
            f"Expiration: {expiration_dt}, "
            f"Type: {contract.contract_type}"
        )
        return await Options.prisma().upsert(
            where={"ticker": contract.ticker},
            data={
                "create": {
                    "ticker": contract.ticker,
                    "underlying_ticker": contract.underlying_ticker,
                    "strike_price": contract.strike_price,
                    "expiration_date": expiration_dt,
                    "contract_type": "CALL" if contract.contract_type == "call" else "PUT",
                },
                "update": {
                    "underlying_ticker": contract.underlying_ticker,
                    "strike_price": contract.strike_price,
                    "expiration_date": expiration_dt,
                    "contract_type": "CALL" if contract.contract_type == "call" else "PUT",
                },
            },
        )

    async def _retrieve_all_option_contracts(self) -> list[Options]:
        try:
            contracts = await Options.prisma().find_many()
            Log.info(f"Retrieved {len(contracts)} option contracts from the database.")
            return contracts
        except Exception as e:
            Log.error(f"Error fetching option contracts: {e}")
            return []

    async def _insert_option_snapshot(
        self,
        contract_ticker: str,
        snapshot: OptionContractSnapshot,
        max_retries: int = 3,
        delay: float = 1.0,
    ) -> OptionSnapshot:
        last_updated_raw = snapshot.day.last_updated if snapshot.day.last_updated else None
        last_updated_dt = ns_to_datetime(last_updated_raw) if last_updated_raw else None
        curr_datetime = self.ingest_time
        attempt = 0
        while attempt < max_retries:
            try:
                if last_updated_dt is None:
                    raise OptionTickerNeverActiveError("last_updated is required")
                result = await db.optionsnapshot.create(
                    data={
                        "open_interest": snapshot.open_interest,
                        "volume": snapshot.day.volume if snapshot.day else None,
                        "implied_vol": snapshot.implied_volatility,
                        "last_price": snapshot.day.close if snapshot.day else None,
                        "last_updated": last_updated_dt,
                        "last_crawled": curr_datetime,
                        "day_open": snapshot.day.open if snapshot.day else None,
                        "day_close": snapshot.day.close if snapshot.day else None,
                        "day_change": snapshot.day.change_percent if snapshot.day else None,
                        "option": {"connect": {"ticker": contract_ticker}},
                    }
                )
                Log.info(
                    f"{curr_datetime} Inserted snapshot for {contract_ticker}: "
                    f"OI={snapshot.open_interest}"
                )
                Log.info(format_snapshot(contract_ticker, snapshot))
                return result
            except UniqueViolationError:
                Log.info(f"{contract_ticker} at {last_updated_dt} has no new update on snapshot")
                break
            except OptionTickerNeverActiveError:
                Log.info(f"{contract_ticker} is not active")
                break
            except Exception as e:
                attempt += 1
                Log.error(
                    f"{curr_datetime} Error inserting option snapshot for "
                    f"{contract_ticker} at {last_updated_dt}: {e} (attempt {attempt}/{max_retries})"
                )
                if attempt < max_retries:
                    await asyncio.sleep(delay)
                else:
                    raise


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
