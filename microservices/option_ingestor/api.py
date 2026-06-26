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
from microservices.shared.observability import start_span_sync
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
SNAPSHOT_FETCH_RETRY_MAX_ATTEMPTS = int(os.getenv("SNAPSHOT_FETCH_RETRY_MAX_ATTEMPTS", "3"))
SNAPSHOT_FETCH_RETRY_BASE_DELAY_SECONDS = float(
    os.getenv("SNAPSHOT_FETCH_RETRY_BASE_DELAY_SECONDS", "0.5")
)
SNAPSHOT_FETCH_RATE_LIMIT_BASE_DELAY_SECONDS = float(
    os.getenv("SNAPSHOT_FETCH_RATE_LIMIT_BASE_DELAY_SECONDS", "15.0")
)
STOCK_SNAPSHOT_FETCH_INTERVAL_SECONDS = float(
    os.getenv("STOCK_SNAPSHOT_FETCH_INTERVAL_SECONDS", "12.0")
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

    @traced_span_sync(name="fetch_chain_snapshots", attributes={"module": "POLYGON"})
    def get_chain_snapshots(self) -> list[OptionContractSnapshot]:
        snapshots: list[OptionContractSnapshot] = []
        for snapshot in self.client.list_snapshot_options_chain(
            self.asset or "",
            params={"limit": 250},
        ):
            if isinstance(snapshot, OptionContractSnapshot):
                snapshots.append(snapshot)
        return snapshots

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
        max_retries = kwargs.get("max_retries", SNAPSHOT_FETCH_RETRY_MAX_ATTEMPTS)
        base_delay_seconds = kwargs.get(
            "base_delay_seconds", SNAPSHOT_FETCH_RETRY_BASE_DELAY_SECONDS
        )
        sanitized_url = _redact_url_query_param(url, "apiKey")
        request_metadata = {
            "underlying_asset": underlying_asset,
            "option_ticker_name": option_ticker_name,
            "url": url,
            "sanitized_url": sanitized_url,
            "connect_timeout": connect_timeout,
            "read_timeout": read_timeout,
        }

        if client is None:
            async with _build_snapshot_async_client(timeout=timeout) as request_client:
                return await self._fetch_snapshot_with_client(
                    request_client=request_client,
                    request_metadata=request_metadata,
                    max_retries=max_retries,
                    base_delay_seconds=base_delay_seconds,
                )

        return await self._fetch_snapshot_with_client(
            request_client=client,
            request_metadata=request_metadata,
            max_retries=max_retries,
            base_delay_seconds=base_delay_seconds,
        )

    @traced_span_async(name="fetch_stock_spot_price", attributes={"module": "POLYGON"})
    async def fetch_stock_spot_price_async(
        self,
        underlying_asset: str,
        *args,
        client: httpx.AsyncClient | None = None,
        **kwargs,
    ) -> float | None:
        url = (
            "https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/"
            f"tickers/{underlying_asset}?apiKey={self.api_key}"
        )
        connect_timeout = kwargs.get("connect_timeout", SNAPSHOT_FETCH_CONNECT_TIMEOUT)
        read_timeout = kwargs.get("read_timeout", SNAPSHOT_FETCH_READ_TIMEOUT)
        timeout = httpx.Timeout(
            connect=connect_timeout,
            read=read_timeout,
            write=read_timeout,
            pool=read_timeout,
        )
        max_retries = kwargs.get("max_retries", SNAPSHOT_FETCH_RETRY_MAX_ATTEMPTS)
        base_delay_seconds = kwargs.get(
            "base_delay_seconds", SNAPSHOT_FETCH_RETRY_BASE_DELAY_SECONDS
        )
        sanitized_url = _redact_url_query_param(url, "apiKey")

        if client is None:
            async with _build_snapshot_async_client(timeout=timeout) as request_client:
                return await self._fetch_stock_spot_price_with_client(
                    request_client=request_client,
                    underlying_asset=underlying_asset,
                    url=url,
                    sanitized_url=sanitized_url,
                    max_retries=max_retries,
                    base_delay_seconds=base_delay_seconds,
                )

        return await self._fetch_stock_spot_price_with_client(
            request_client=client,
            underlying_asset=underlying_asset,
            url=url,
            sanitized_url=sanitized_url,
            max_retries=max_retries,
            base_delay_seconds=base_delay_seconds,
        )

    async def _fetch_snapshot_with_client(
        self,
        request_client: httpx.AsyncClient,
        request_metadata: dict[str, str | float],
        max_retries: int,
        base_delay_seconds: float,
    ) -> OptionContractSnapshot | None:
        underlying_asset = str(request_metadata["underlying_asset"])
        option_ticker_name = str(request_metadata["option_ticker_name"])
        url = str(request_metadata["url"])
        sanitized_url = str(request_metadata["sanitized_url"])
        connect_timeout = float(request_metadata["connect_timeout"])
        read_timeout = float(request_metadata["read_timeout"])

        for attempt in range(1, max_retries + 1):
            try:
                response = await request_client.get(url)
                response.raise_for_status()
                logger.info(
                    f"Fetched snapshot for {underlying_asset}/{option_ticker_name} successfully."
                )
                with start_span_sync(
                    "transform_snapshot_response",
                    attributes={
                        "module": "TRANSFORM",
                        "underlying_asset": underlying_asset,
                        "option_ticker_name": option_ticker_name,
                    },
                ):
                    return OptionContractSnapshot.from_dict(response.json().get("results"))
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == NOT_FOUND_STATUS_CODE:
                    logger.warning(
                        f"Option not found or expired: {underlying_asset}/{option_ticker_name}"
                        f"(URL: {sanitized_url})"
                    )
                    return None

                if _is_rate_limited_response(exc.response):
                    retry_after_seconds = _retry_after_seconds(exc.response)
                    delay = retry_after_seconds or (
                        SNAPSHOT_FETCH_RATE_LIMIT_BASE_DELAY_SECONDS * (2 ** (attempt - 1))
                    )
                    if attempt < max_retries:
                        logger.warning(
                            "Polygon rate limited snapshot fetch; retrying "
                            "| underlying_asset=%s, option_ticker_name=%s, "
                            "status_code=%s, retry_after=%s, delay=%.2fs, attempt=%s/%s, url=%s",
                            underlying_asset,
                            option_ticker_name,
                            exc.response.status_code,
                            exc.response.headers.get("Retry-After"),
                            delay,
                            attempt,
                            max_retries,
                            sanitized_url,
                        )
                        await asyncio.sleep(delay)
                        continue

                    logger.error(
                        "Polygon rate limit exhausted for snapshot fetch "
                        "| underlying_asset=%s, option_ticker_name=%s, "
                        "status_code=%s, retry_after=%s, attempts=%s, url=%s",
                        underlying_asset,
                        option_ticker_name,
                        exc.response.status_code,
                        exc.response.headers.get("Retry-After"),
                        max_retries,
                        sanitized_url,
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
                if not _is_retryable_snapshot_request_error(exc) or attempt >= max_retries:
                    logger.error(
                        "Request error fetching snapshot: %s | underlying_asset=%s, "
                        "option_ticker_name=%s, url=%s",
                        type(exc).__name__,
                        underlying_asset,
                        option_ticker_name,
                        sanitized_url,
                    )
                    return None

                delay = base_delay_seconds * (2 ** (attempt - 1))
                logger.warning(
                    "Retrying snapshot fetch after transient request error: %s "
                    "| underlying_asset=%s, option_ticker_name=%s, "
                    "connect_timeout=%s, read_timeout=%s, delay=%.2fs, attempt=%s/%s, url=%s",
                    type(exc).__name__,
                    underlying_asset,
                    option_ticker_name,
                    connect_timeout,
                    read_timeout,
                    delay,
                    attempt,
                    max_retries,
                    sanitized_url,
                )
                await asyncio.sleep(delay)

        return None

    async def _fetch_stock_spot_price_with_client(
        self,
        request_client: httpx.AsyncClient,
        underlying_asset: str,
        url: str,
        sanitized_url: str,
        max_retries: int,
        base_delay_seconds: float,
    ) -> float | None:
        for attempt in range(1, max_retries + 1):
            try:
                response = await request_client.get(url)
                response.raise_for_status()
                price = _extract_stock_spot_price(response.json())
                if price is None:
                    logger.warning(
                        "Stock spot price missing from snapshot payload | underlying_asset=%s, url=%s",
                        underlying_asset,
                        sanitized_url,
                    )
                    return None
                logger.info(
                    "Fetched stock spot price successfully | underlying_asset=%s, price=%s",
                    underlying_asset,
                    price,
                )
                return price
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == NOT_FOUND_STATUS_CODE:
                    logger.warning(
                        "Stock snapshot not found: %s (URL: %s)",
                        underlying_asset,
                        sanitized_url,
                    )
                    return None

                if _is_rate_limited_response(exc.response):
                    retry_after_seconds = _retry_after_seconds(exc.response)
                    delay = retry_after_seconds or (
                        SNAPSHOT_FETCH_RATE_LIMIT_BASE_DELAY_SECONDS * (2 ** (attempt - 1))
                    )
                    if attempt < max_retries:
                        logger.warning(
                            "Polygon rate limited stock spot fetch; retrying "
                            "| underlying_asset=%s, status_code=%s, retry_after=%s, "
                            "delay=%.2fs, attempt=%s/%s, url=%s",
                            underlying_asset,
                            exc.response.status_code,
                            exc.response.headers.get("Retry-After"),
                            delay,
                            attempt,
                            max_retries,
                            sanitized_url,
                        )
                        await asyncio.sleep(delay)
                        continue

                    logger.error(
                        "Polygon rate limit exhausted for stock spot fetch "
                        "| underlying_asset=%s, status_code=%s, retry_after=%s, "
                        "attempts=%s, url=%s",
                        underlying_asset,
                        exc.response.status_code,
                        exc.response.headers.get("Retry-After"),
                        max_retries,
                        sanitized_url,
                    )
                    return None

                logger.error(
                    "HTTP error %s fetching stock spot: %s | underlying_asset=%s, url=%s",
                    exc.response.status_code,
                    exc.response.text,
                    underlying_asset,
                    sanitized_url,
                )
                return None
            except httpx.RequestError as exc:
                if not _is_retryable_snapshot_request_error(exc) or attempt >= max_retries:
                    logger.error(
                        "Request error fetching stock spot: %s | underlying_asset=%s, url=%s",
                        type(exc).__name__,
                        underlying_asset,
                        sanitized_url,
                    )
                    return None

                delay = base_delay_seconds * (2 ** (attempt - 1))
                logger.warning(
                    "Retrying stock spot fetch after transient request error: %s "
                    "| underlying_asset=%s, delay=%.2fs, attempt=%s/%s, url=%s",
                    type(exc).__name__,
                    underlying_asset,
                    delay,
                    attempt,
                    max_retries,
                    sanitized_url,
                )
                await asyncio.sleep(delay)

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
                        option_fetcher,
                        contract,
                        *args,
                        client=client,
                        semaphore=fetch_semaphore,
                        **kwargs,
                    )
                )
                for contract in contracts_batch
            ]
            results.extend(await asyncio.gather(*tasks))
    return results


async def fetch_chain_snapshots_for_underlying(underlying_asset: str) -> list[OptionContractSnapshot]:
    option_fetcher = Fetcher(underlying_asset)
    return await asyncio.to_thread(option_fetcher.get_chain_snapshots)


async def fetch_stock_spot_price(
    underlying_asset: str,
    *args,
    client: httpx.AsyncClient | None = None,
    **kwargs,
) -> float | None:
    option_fetcher = Fetcher(None)
    return await option_fetcher.fetch_stock_spot_price_async(
        underlying_asset,
        *args,
        client=client,
        **kwargs,
    )


async def fetch_stock_spot_prices_for_underlyings(
    underlying_assets: list[str],
    *args,
    **kwargs,
) -> dict[str, float | None]:
    if not underlying_assets:
        return {}

    timeout = httpx.Timeout(
        connect=kwargs.get("connect_timeout", SNAPSHOT_FETCH_CONNECT_TIMEOUT),
        read=kwargs.get("read_timeout", SNAPSHOT_FETCH_READ_TIMEOUT),
        write=kwargs.get("read_timeout", SNAPSHOT_FETCH_READ_TIMEOUT),
        pool=kwargs.get("read_timeout", SNAPSHOT_FETCH_READ_TIMEOUT),
    )
    prices: dict[str, float | None] = {}
    async with _build_snapshot_async_client(timeout=timeout) as client:
        for index, underlying_asset in enumerate(underlying_assets):
            if index > 0 and STOCK_SNAPSHOT_FETCH_INTERVAL_SECONDS > 0:
                await asyncio.sleep(STOCK_SNAPSHOT_FETCH_INTERVAL_SECONDS)
            prices[underlying_asset] = await fetch_stock_spot_price(
                underlying_asset,
                *args,
                client=client,
                **kwargs,
            )
    return prices


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
        try:
            return await option_fetcher.fetch_daily_snapshot_async(
                contract.underlying_ticker,
                contract.ticker,
                *args,
                client=client,
                **kwargs,
            )
        except Exception:
            logger.exception(
                "Unexpected error fetching snapshot | underlying_asset=%s, option_ticker_name=%s",
                contract.underlying_ticker,
                contract.ticker,
            )
            return None


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


def _is_retryable_snapshot_request_error(error: httpx.RequestError) -> bool:
    return isinstance(error, httpx.ConnectTimeout | httpx.ReadTimeout)


def _is_rate_limited_response(response: httpx.Response) -> bool:
    return response.status_code == 429


def _retry_after_seconds(response: httpx.Response) -> float | None:
    retry_after = response.headers.get("Retry-After")
    if retry_after is None:
        return None
    try:
        return max(0.0, float(retry_after))
    except ValueError:
        return None


def _extract_stock_spot_price(payload: dict) -> float | None:
    ticker_data = payload.get("ticker")
    if not isinstance(ticker_data, dict):
        return None
    last_trade = ticker_data.get("lastTrade")
    if isinstance(last_trade, dict) and last_trade.get("p") is not None:
        return float(last_trade["p"])
    minute_bar = ticker_data.get("min")
    if isinstance(minute_bar, dict) and minute_bar.get("c") is not None:
        return float(minute_bar["c"])
    day_bar = ticker_data.get("day")
    if isinstance(day_bar, dict) and day_bar.get("c") is not None:
        return float(day_bar["c"])
    previous_day_bar = ticker_data.get("prevDay")
    if isinstance(previous_day_bar, dict) and previous_day_bar.get("c") is not None:
        return float(previous_day_bar["c"])
    return None


__all__ = [
    "Fetcher",
    "fetch_chain_snapshots_for_underlying",
    "fetch_stock_spot_price",
    "fetch_stock_spot_prices_for_underlyings",
    "get_contract_within_price_range",
    "fetch_snapshots_batch",
]
