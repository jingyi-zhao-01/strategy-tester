import asyncio
import os

import httpx
from polygon import RESTClient

from ..models import OptionContractSnapshot, OptionsContract
from ..util import parse_option_symbol


class Core:
    def __init__(self, asset: str = None):
        self.asset = asset
        self.api_key = os.getenv("POLYGON_API_KEY")
        if not self.api_key:
            raise ValueError("POLYGON_API_KEY environment variable is not set")
        self.client = RESTClient(self.api_key)

    def get_call_contracts(self) -> list[OptionsContract]:
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

    def get_put_contracts(self) -> list[OptionsContract]:
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


async def fetch_snapshots_batch(contracts: list[OptionsContract]) -> list[OptionContractSnapshot]:
    option_fetcher = Core(None)

    tasks = [
        option_fetcher.get_contract_snapshot_async(contract.underlying_ticker, contract.ticker)
        for contract in contracts
    ]

    return await asyncio.gather(*tasks)
