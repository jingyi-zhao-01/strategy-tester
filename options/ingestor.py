import asyncio
import os

import httpx
from polygon import RESTClient

from lib import Log

from .models import OptionContractSnapshot, OptionsContract
from .operations import (
    db,
    get_all_option_contracts,
    process_option_contracts,
    process_option_snapshot,
)
from .util import parse_option_symbol

# TODO: Open Interest vs expiration date vs strike price


class Core:
    def __init__(self, asset: str = None):
        self.asset = asset
        self.api_key = os.getenv("POLYGON_API_KEY")
        if not self.api_key:
            raise ValueError("POLYGON_API_KEY environment variable is not set")
        self.client = RESTClient(self.api_key)

    def get_call_contracts_sync(self) -> list[OptionsContract]:
        contracts: list[OptionsContract] = []
        for contract in self.client.list_options_contracts(
            underlying_ticker=self.asset,
            contract_type="call",
            expired="false",
            order="desc",
            sort="strike_price",
        ):
            contracts.append(contract)
        return contracts

    def get_put_contracts_sync(self) -> list[OptionsContract]:
        contracts: list[OptionsContract] = []
        for contract in self.client.list_options_contracts(
            underlying_ticker=self.asset,
            contract_type="put",
            expired="false",
            order="desc",
            sort="strike_price",
        ):
            contracts.append(contract)
        return contracts

    def get_contract_snapshot(
        self, underlying_asset: str, option_ticker_name: str
    ) -> OptionContractSnapshot:
        snapshot = self.client.get_snapshot_option(underlying_asset, option_ticker_name)
        return snapshot

    async def get_contract_snapshot_async(
        self, underlying_asset: str, option_ticker_name: str
    ) -> OptionContractSnapshot:
        url = f"https://api.polygon.io/v3/snapshot/options/{underlying_asset}/{option_ticker_name}?apiKey={self.api_key}"

        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            return OptionContractSnapshot.from_dict(response.json().get("results"))


async def fetch_snapshots_batch(contracts: list[OptionsContract]) -> list[OptionContractSnapshot]:
    option_fetcher = Core(None)

    tasks = [
        option_fetcher.get_contract_snapshot_async(contract.underlying_ticker, contract.ticker)
        for contract in contracts
    ]

    return await asyncio.gather(*tasks)


def get_contract_within_price_range(
    contracts: list[OptionsContract],
    price_range: tuple[float, float],
    year_range: tuple[int, int] = None,
) -> list[OptionContractSnapshot]:
    min_price, max_price = price_range
    start_year, end_year = year_range if year_range else (None, None)
    return [
        contract
        for contract in contracts
        if min_price <= contract.strike_price <= max_price
        and (
            parse_option_symbol(contract.ticker, contract.underlying_ticker).expiration.year
            >= start_year
            if start_year
            else True
        )
        and (
            parse_option_symbol(contract.ticker, contract.underlying_ticker).expiration.year
            <= end_year
            if end_year
            else True
        )
    ]


async def ingest_options(
    underlying_asset: str, price_range: tuple[float, float], year_range: tuple[int, int]
):
    await db.connect()
    try:
        core = Core(underlying_asset)
        calls = core.get_call_contracts_sync()
        puts = core.get_put_contracts_sync()

        contracts = calls + puts
        Log.info(f"Total contracts found: {len(contracts)}")

        contracts_within_range = get_contract_within_price_range(contracts, price_range, year_range)
        Log.info(f"Contracts within price range: {len(contracts_within_range)}")

        # Only process contracts, no snapshots
        await asyncio.gather(
            *[process_option_contracts(db, contract) for contract in contracts_within_range]
        )
        Log.info("All contracts processed successfully")
    except Exception as e:
        Log.error(f"Error during options ingestion: {e}")
        raise e
    finally:
        await db.disconnect()


async def ingest_option_snapshots():
    await db.connect()
    try:
        # core = Core(underlying_asset)
        # calls = core.get_call_contracts_sync()
        # puts = core.get_put_contracts_sync()

        # contracts = calls + puts

        contracts = await get_all_option_contracts(db)

        # contracts_within_range = get_contract_within_price_range(contracts, None, None)
        Log.info(f"Existing Contracts in database: {len(contracts)}")

        snapshots = await fetch_snapshots_batch(contracts)

        await asyncio.gather(
            *[
                process_option_snapshot(db, contract.ticker, snapshot)
                for contract, snapshot in zip(contracts, snapshots)
            ]
        )

        Log.info("All option snapshots processed successfully")

    except Exception as e:
        Log.error(f"Error during option snapshots ingestion: {e}")
        raise e
    finally:
        await db.disconnect()


if __name__ == "__main__":
    LIMIT = 5

    ASSET = "SE"
    LIMIT = 100
    PRICE_RANGE = (140, 200)
    YEAR_RANGE = (2025, 2025)

    UNDERLYING_ASSET = "NBIS"
    PRICE_RANGE = (40, 70)
    YEAR_RANGE = (2025, 2025)

    ASSET = "HOOD"
    PRICE_RANGE = (100, 150)
    YEAR_RANGE = (2025, 2025)

    ASSET = "FCX"
    PRICE_RANGE = (45, 50)
    YEAR_RANGE = (2025, 2025)
    # asyncio.run(ingest_options(UNDERLYING_ASSET, PRICE_RANGE, YEAR_RANGE))
    asyncio.run(ingest_option_snapshots())


__all__ = ["ingest_options", "ingest_option_snapshots"]
