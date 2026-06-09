import asyncio
import logging
import os
from typing import TYPE_CHECKING
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
from polygon import RESTClient

from microservices.shared.decorator import (
    traced_span_async,
    traced_span_sync,
)
from microservices.shared.models import OptionContractSnapshot, OptionsContract
from microservices.shared.util import parse_option_symbol

if TYPE_CHECKING:  # pragma: no cover
    from prisma.models import Options  # type: ignore


NOT_FOUND_STATUS_CODE = 404
SNAPSHOT_FETCH_CONCURRENCY = int(os.getenv("SNAPSHOT_FETCH_CONCURRENCY", "300"))
SNAPSHOT_FETCH_CONNECT_TIMEOUT = float(os.getenv("SNAPSHOT_FETCH_CONNECT_TIMEOUT", "10.0"))
SNAPSHOT_FETCH_READ_TIMEOUT = float(os.getenv("SNAPSHOT_FETCH_READ_TIMEOUT", "10.0"))
SNAPSHOT_FETCH_BATCH_SIZE = int(os.getenv("SNAPSHOT_FETCH_BATCH_SIZE", "25"))
SNAPSHOT_HTTP_MAX_CONNECTIONS = int(os.getenv("SNAPSHOT_HTTP_MAX_CONNECTIONS", "50"))
SNAPSHOT_HTTP_MAX_KEEPALIVE_CONNECTIONS = int(
    os.getenv("SNAPSHOT_HTTP_MAX_KEEPALIVE_CONNECTIONS", "20")
)
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
        self,
        underlying_asset: str,
        option_ticker_name: str,
        *args,
        client: httpx.AsyncClient | None = None,
        **kwargs,
    ) -> OptionContractSnapshot | None:
        url = f"https://api.polygon.io/v3/snapshot/options/{underlying_asset}/{option_ticker_name}?apiKey={self.api_key}"

        connect_timeout = kwargs.get("connect_timeout", SNAPSHOT_FETCH_CONNECT_TIMEOUT)
        read_timeout = kwargs.get("read_timeout", SNAPSHOT_FETCH_READ_TIMEOUT)
        timeout = httpx.Timeout(
            connect=connect_timeout,
            read=read_timeout,
            write=read_timeout,
            pool=read_timeout,
        )
        sanitized_url = _redact_url_query_param(url, "apiKey")

        if client is None:
            async with _build_snapshot_async_client(timeout=timeout) as request_client:
                return await self._fetch_snapshot_with_client(
                    request_client=request_client,
                    underlying_asset=underlying_asset,
                    option_ticker_name=option_ticker_name,
                    url=url,
                    sanitized_url=sanitized_url,
                    connect_timeout=connect_timeout,
                )

        return await self._fetch_snapshot_with_client(
            request_client=client,
            underlying_asset=underlying_asset,
            option_ticker_name=option_ticker_name,
            url=url,
            sanitized_url=sanitized_url,
            connect_timeout=connect_timeout,
        )

    async def _fetch_snapshot_with_client(
        self,
        request_client: httpx.AsyncClient,
        underlying_asset: str,
        option_ticker_name: str,
        url: str,
        sanitized_url: str,
        connect_timeout: float,
    ) -> OptionContractSnapshot | None:
        try:
            response = await request_client.get(url)
            response.raise_for_status()
            logger.info(
                f"Fetched snapshot for {underlying_asset}/{option_ticker_name} successfully."
            )
            return OptionContractSnapshot.from_dict(response.json().get("results"))
        except httpx.ConnectTimeout:
            logger.error(
                "Connect timeout fetching snapshot | underlying_asset=%s, "
                "option_ticker_name=%s, timeout=%s, url=%s",
                underlying_asset,
                option_ticker_name,
                connect_timeout,
                sanitized_url,
            )
            return None
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == NOT_FOUND_STATUS_CODE:
                logger.warning(
                    f"Option not found or expired: {underlying_asset}/{option_ticker_name}"
                    f"(URL: {sanitized_url})"
                )
                return None

            logger.error(
                "HTTP error %s: %s | underlying_asset=%s, option_ticker_name=%s, url=%s",
                exc.response.status_code,
                exc.response.text,
                underlying_asset,
                option_ticker_name,
                sanitized_url,
            )
            return None
        except httpx.RequestError as exc:
            logger.error(
                "Request error fetching snapshot: %s | underlying_asset=%s, "
                "option_ticker_name=%s, url=%s",
                type(exc).__name__,
                underlying_asset,
                option_ticker_name,
                sanitized_url,
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


async def fetch_snapshots_batch(
    contracts: list["Options"], *args, **kwargs
) -> list[OptionContractSnapshot | None]:
    option_fetcher = Fetcher(None)
    timeout = httpx.Timeout(
        connect=kwargs.get("connect_timeout", SNAPSHOT_FETCH_CONNECT_TIMEOUT),
        read=kwargs.get("read_timeout", SNAPSHOT_FETCH_READ_TIMEOUT),
        write=kwargs.get("read_timeout", SNAPSHOT_FETCH_READ_TIMEOUT),
        pool=kwargs.get("read_timeout", SNAPSHOT_FETCH_READ_TIMEOUT),
    )
    fetch_semaphore = asyncio.Semaphore(max(1, SNAPSHOT_FETCH_CONCURRENCY))
    results: list[OptionContractSnapshot | None] = []
    async with _build_snapshot_async_client(timeout=timeout) as client:
        for contracts_batch in _iter_contract_batches(contracts, SNAPSHOT_FETCH_BATCH_SIZE):
            tasks = [
                asyncio.create_task(
                    _fetch_snapshot_with_limit(
                        option_fetcher=option_fetcher,
                        contract=contract,
                        client=client,
                        semaphore=fetch_semaphore,
                        *args,
                        **kwargs,
                    )
                )
                for contract in contracts_batch
            ]
            results.extend(await asyncio.gather(*tasks))
    return results


def _build_snapshot_async_client(timeout: httpx.Timeout) -> httpx.AsyncClient:
    limits = httpx.Limits(
        max_connections=SNAPSHOT_HTTP_MAX_CONNECTIONS,
        max_keepalive_connections=SNAPSHOT_HTTP_MAX_KEEPALIVE_CONNECTIONS,
    )
    return httpx.AsyncClient(timeout=timeout, limits=limits)


async def _fetch_snapshot_with_limit(
    option_fetcher: Fetcher,
    contract: "Options",
    *args,
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    **kwargs,
) -> OptionContractSnapshot | None:
    async with semaphore:
        return await option_fetcher.fetch_daily_snapshot_async(
            contract.underlying_ticker,
            contract.ticker,
            *args,
            client=client,
            **kwargs,
        )


def _iter_contract_batches(contracts: list["Options"], batch_size: int) -> list[list["Options"]]:
    normalized_batch_size = max(1, batch_size)
    return [
        contracts[index : index + normalized_batch_size]
        for index in range(0, len(contracts), normalized_batch_size)
    ]


def _redact_url_query_param(url: str, param_name: str) -> str:
    parts = urlsplit(url)
    sanitized_query = urlencode(
        [
            (key, "[REDACTED]" if key == param_name else value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
        ]
    )
    return urlunsplit((parts.scheme, parts.netloc, parts.path, sanitized_query, parts.fragment))


__all__ = ["Fetcher", "get_contract_within_price_range", "fetch_snapshots_batch"]
