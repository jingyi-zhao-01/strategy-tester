from util import get_polygon_client, parse_option_symbol
from models import OptionsContract, OptionContractSnapshot

from typing import List
from operations import process_option_contract, process_option_snapshot

LIMIT = 10

# ASSET = "SE"
# LIMIT = 100
# PRICE_RANGE = (140, 200)
# YEAR_RANGE = (2025, 2025)


ASSET = "NBIS"
PRICE_RANGE = (55, 70)
YEAR_RANGE = (2025, 2025)


# ASSET = "HOOD"
# PRICE_RANGE = (100, 150)
# YEAR_RANGE = (2025, 2025)


# ASSET = "FCX"
# PRICE_RANGE = (45, 50)
# YEAR_RANGE = (2025, 2025)


client = get_polygon_client()

# TODO: Open Interest vs expiration date vs strike price


class OptionFetcher:
    def __init__(self, asset: str):
        self.asset = asset
        self.client = get_polygon_client()

    def get_contracts(self) -> List[OptionsContract]:
        contracts: List[OptionsContract] = []
        for contract in self.client.list_options_contracts(
            underlying_ticker=self.asset,
            contract_type="call",
            # strike_price=55,
            expired="false",
            order="desc",
            # limit=20,
            sort="strike_price",
        ):
            contracts.append(contract)
        return contracts

    def get_contract_within_price_range(
        self,
        contracts: List[OptionsContract],
        price_range: tuple[float, float],
        year_range: tuple[int, int] = None,
    ) -> List[OptionContractSnapshot]:
        min_price, max_price = price_range
        start_year, end_year = year_range if year_range else (None, None)
        return [
            contract
            for contract in contracts
            if min_price <= contract.strike_price <= max_price
            and (
                parse_option_symbol(contract.ticker, ASSET).expiration.year
                >= start_year
                if start_year
                else True
            )
            and (
                parse_option_symbol(contract.ticker, ASSET).expiration.year <= end_year
                if end_year
                else True
            )
        ]

    def get_contract_snapshot(
        self, underlying_asset: str, option_ticker_name: str
    ) -> OptionContractSnapshot:
        client = get_polygon_client()
        snapshot = client.get_snapshot_option(underlying_asset, option_ticker_name)
        return snapshot

    def format_snapshot(
        self, contract: OptionsContract, snapshot: OptionContractSnapshot
    ) -> str:
        return (
            f"Ticker: {contract.ticker} | "
            f"OI: {snapshot.open_interest or 'N/A'} | "
            f"Day Volume: {snapshot.day.volume or 'N/A'} | "
            f"IV: {f'{snapshot.implied_volatility:.2%}' if snapshot.implied_volatility else 'N/A'} | "
            # f"Greeks: {snapshot.greeks or 'N/A'} | "
            f"DayOpen: {f'${snapshot.day.open:.2f}' if snapshot.day.open else 'N/A'} | "
            f"DayClose: {f'${snapshot.day.close:.2f}' if snapshot.day.close else 'N/A'} | "
            f"Day Price Change: {f'{snapshot.day.change_percent:.2f}%' if snapshot.day.change_percent else 'N/A'} | "
            f"Last Updated: {snapshot.day.last_updated or 'N/A'}"
        )


async def main():

    option_fetcher = OptionFetcher(ASSET)
    contracts = option_fetcher.get_contracts()
    print(f"Total contracts found: {len(contracts)}")

    contracts_within_range = option_fetcher.get_contract_within_price_range(
        contracts, PRICE_RANGE, YEAR_RANGE
    )

    print(f"Contracts within price range: {len(contracts_within_range)}")

    for contract in contracts_within_range[:LIMIT]:
        db_contract = await process_option_contract(contract)
        print(f"Upserted contract: {db_contract.ticker}")

        snapshot = option_fetcher.get_contract_snapshot(
            contract.underlying_ticker, contract.ticker
        )
        db_snapshot = await process_option_snapshot(contract.ticker, snapshot)
        print(f"Added snapshot for {contract.ticker}: OI={db_snapshot.openInterest}")

        print(option_fetcher.format_snapshot(contract, snapshot))
        print("-" * 80)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
