import asyncio
import os

import httpx
from log import Log
from models import OptionContractSnapshot, OptionsContract
from operations import db, process_option_contracts, process_option_snapshot
from polygon import RESTClient
from util import parse_option_symbol

LIMIT = 5

# ASSET = "SE"
# LIMIT = 100
# PRICE_RANGE = (140, 200)
# YEAR_RANGE = (2025, 2025)


UNDERLYING_ASSET = "NBIS"
PRICE_RANGE = (40, 70)
YEAR_RANGE = (2025, 2025)


# ASSET = "HOOD"
# PRICE_RANGE = (100, 150)
# YEAR_RANGE = (2025, 2025)


# ASSET = "FCX"
# PRICE_RANGE = (45, 50)
# YEAR_RANGE = (2025, 2025)


# TODO: Open Interest vs expiration date vs strike price


class Core:
    def __init__(self, asset: str):
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


async def fetch_snapshots_batch(contracts, underlying_asset):
    option_fetcher = Core(UNDERLYING_ASSET)

    tasks = [
        option_fetcher.get_contract_snapshot_async(underlying_asset, contract.ticker)
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
            parse_option_symbol(contract.ticker, UNDERLYING_ASSET).expiration.year >= start_year
            if start_year
            else True
        )
        and (
            parse_option_symbol(contract.ticker, UNDERLYING_ASSET).expiration.year <= end_year
            if end_year
            else True
        )
    ]


async def process_contract_and_snapshot(contract, snapshot):
    await process_option_contracts(db, contract)
    await process_option_snapshot(db, contract.ticker, snapshot)


async def main():
    await db.connect()
    try:
        core = Core(UNDERLYING_ASSET)
        calls = core.get_call_contracts_sync()
        puts = core.get_put_contracts_sync()

        contracts = calls + puts
        Log.info(f"Total contracts found: {len(contracts)}")

        contracts_within_range = get_contract_within_price_range(contracts, PRICE_RANGE, YEAR_RANGE)

        Log.info(f"Contracts within price range: {len(contracts_within_range)}")

        snapshots = await fetch_snapshots_batch(contracts_within_range, UNDERLYING_ASSET)

        await asyncio.gather(
            *[
                process_contract_and_snapshot(contract, snapshot)
                for contract, snapshot in zip(contracts_within_range, snapshots)
            ]
        )
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
