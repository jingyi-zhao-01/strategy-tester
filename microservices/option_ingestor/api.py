import asyncio
import logging
import os
from typing import TYPE_CHECKING

import httpx
from polygon import RESTClient

from microservices.shared.decorator import (
    bounded_async_sem,
    traced_span_async,
    traced_span_sync,
)
from microservices.shared.models import OptionContractSnapshot, OptionsContract
from microservices.shared.util import parse_option_symbol

if TYPE_CHECKING:  # pragma: no cover
    from prisma.models import Options  # type: ignore


NOT_FOUND_STATUS_CODE = 404
SNAPSHOT_FETCH_CONCURRENCY = int(os.getenv("SNAPSHOT_FETCH_CONCURRENCY", "300"))
logger = logging.getLogger(__name__)


class Fetcher:
    def __init__(self, asset: str | None = None):
        self.asset: str | None = asset
        self.api_key = os.getenv("POLYGON_API_KEY")
        if not self.api_key:
            raise ValueError("POLYGON_API_KEY environment variable is not set")
        self.client = RESTClient(self.api_key)

    @traced_span_sync(name="fetch_call_contracts", attributes={"module": "POLYGON"})
    def get_call_contracts(self) -> list[OptionsContract]:
        contracts: list[OptionsContract] = []
        for contract in self.client.list_options_contracts(
            underlying_ticker=self.asset or "",
            contract_type="call",
            expired=False,
            order="desc",
            sort="strike_price",
        ):
            if isinstance(contract, OptionsContract):
                contracts.append(contract)
        return contracts

    @traced_span_sync(name="fetch_put_contracts", attributes={"module": "POLYGON"})
    def get_put_contracts(self) -> list[OptionsContract]:
        contracts: list[OptionsContract] = []
        for contract in self.client.list_options_contracts(
            underlying_ticker=self.asset or "",
            contract_type="put",
            expired=False,
            order="desc",
            sort="strike_price",
        ):
            if isinstance(contract, OptionsContract):
                contracts.append(contract)
        return contracts

    @traced_span_async(name="fetch_daily_snapshot", attributes={"module": "POLYGON"})
    async def fetch_daily_snapshot_async(
        self, underlying_asset: str, option_ticker_name: str, *args, **kwargs
    ) -> OptionContractSnapshot | None:
        url = f"https://api.polygon.io/v3/snapshot/options/{underlying_asset}/{option_ticker_name}?apiKey={self.api_key}"

        timeout = kwargs.get("timeout", 10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                logger.info(
                    f"Fetched snapshot for {underlying_asset}/{option_ticker_name} successfully."
                )
                return OptionContractSnapshot.from_dict(response.json().get("results"))
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == NOT_FOUND_STATUS_CODE:
                    logger.warning(
                        f"Option not found or expired: {underlying_asset}/{option_ticker_name}"
                        f"(URL: {url})"
                    )
                    return None

                logger.exception(
                    f"HTTP error {exc.response.status_code}: {exc.response.text} | "
                    f"underlying_asset={underlying_asset}, "
                    f"option_ticker_name={option_ticker_name}, "
                    f"url={url}"
                )
                return None


def get_contract_within_price_range(
    contracts: list[OptionsContract],
    price_range: tuple[float, float],
    year_range: tuple[int, int] | None = None,
) -> list[OptionsContract]:
    min_price, max_price = price_range
    start_year, end_year = year_range if year_range else (None, None)
    return [
        contract
        for contract in contracts
        if (contract.strike_price is not None and min_price <= contract.strike_price <= max_price)
        and (
            parse_option_symbol(
                contract.ticker or "", contract.underlying_ticker or ""
            ).expiration.year
            >= start_year
            if start_year
            else True
        )
        and (
            parse_option_symbol(
                contract.ticker or "", contract.underlying_ticker or ""
            ).expiration.year
            <= end_year
            if end_year
            else True
        )
    ]


@bounded_async_sem(limit=SNAPSHOT_FETCH_CONCURRENCY)
async def fetch_snapshots_batch(
    contracts: list["Options"], *args, **kwargs
) -> list[OptionContractSnapshot]:
    option_fetcher = Fetcher(None)
    tasks = [
        option_fetcher.fetch_daily_snapshot_async(
            contract.underlying_ticker, contract.ticker, *args, **kwargs
        )
        for contract in contracts
    ]
    results = await asyncio.gather(*tasks)
    return [snapshot for snapshot in results if snapshot is not None]


__all__ = ["Fetcher", "get_contract_within_price_range", "fetch_snapshots_batch"]
