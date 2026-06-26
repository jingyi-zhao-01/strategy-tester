import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from microservices.option_ingestor import api as option_api
from microservices.option_ingestor.ingestor import OptionIngestor
from microservices.shared.errors import OptionTickerNeverActiveError
from microservices.shared.models import OptionIngestParams, OptionsContract
from microservices.snapshot_ingestor.ingestor import (
    OptionSnapshotsIngestor,
    _build_snapshot_upsert_payload,
)
from prisma.errors import ClientNotConnectedError

EXPECTED_RETRY_UPSERT_CALLS = 2
EXPECTED_RETRY_FETCH_CALLS = 2


@pytest.fixture
def mock_option_retriever():
    mock = MagicMock()
    mock.with_ingest_time.return_value = mock
    mock.retrieve_active = AsyncMock(return_value=[])

    async def empty_async_gen():
        for _ in ():
            yield _

    mock.stream_retrieve = empty_async_gen
    return mock


@pytest.fixture
def ingestor(mock_option_retriever):
    return OptionIngestor(option_retriever=mock_option_retriever)


@pytest.fixture
def snapshots_ingestor(mock_option_retriever):
    return OptionSnapshotsIngestor(option_retriever=mock_option_retriever)


@pytest.mark.asyncio
async def test_ingest_options_empty(monkeypatch, ingestor):
    monkeypatch.setattr(
        "microservices.option_ingestor.ingestor.Fetcher",
        lambda asset: MagicMock(get_call_contracts=lambda: [], get_put_contracts=lambda: []),
    )
    await ingestor.ingest_options([OptionIngestParams("TEST", (0, 1), (2025, 2025))])


@pytest.mark.asyncio
async def test_ingest_option_snapshots_empty(snapshots_ingestor):
    await snapshots_ingestor.ingest_option_snapshots()


@pytest.mark.asyncio
async def test_ingest_option_snapshots_uses_paginated_chain_results(
    monkeypatch, snapshots_ingestor
):
    contract_a = MagicMock(ticker="O:TST1", underlying_ticker="TST")
    contract_b = MagicMock(ticker="O:TST2", underlying_ticker="TST")
    snapshots_ingestor.option_retriever.retrieve_active = AsyncMock(
        return_value=[contract_a, contract_b]
    )

    snapshot_a = MagicMock()
    snapshot_a.details = MagicMock(ticker="O:TST1")
    snapshot_b = MagicMock()
    snapshot_b.details = MagicMock(ticker="O:TST2")
    snapshot_extra = MagicMock()
    snapshot_extra.details = MagicMock(ticker="O:OTHER")

    monkeypatch.setattr(
        "microservices.snapshot_ingestor.ingestor.fetch_chain_snapshots_for_underlying",
        AsyncMock(return_value=[snapshot_a, snapshot_b, snapshot_extra]),
    )
    snapshots_ingestor._upsert_option_snapshot = AsyncMock()

    await snapshots_ingestor.ingest_option_snapshots()

    assert snapshots_ingestor._upsert_option_snapshot.await_count == 2
    snapshots_ingestor._upsert_option_snapshot.assert_any_await("O:TST1", snapshot_a)
    snapshots_ingestor._upsert_option_snapshot.assert_any_await("O:TST2", snapshot_b)


@pytest.mark.asyncio
async def test_fetch_snapshots_batch_chunks_requests_and_preserves_results(monkeypatch):
    class _FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    contracts = [
        MagicMock(underlying_ticker="NBIS", ticker="O:NBIS1"),
        MagicMock(underlying_ticker="NBIS", ticker="O:NBIS2"),
        MagicMock(underlying_ticker="NBIS", ticker="O:NBIS3"),
    ]
    active = 0
    max_active = 0
    seen_tickers = []

    class _FakeFetcher:
        def __init__(self, _asset):
            pass

        async def fetch_daily_snapshot_async(
            self,
            underlying_asset,
            option_ticker_name,
            *args,
            client=None,
            **kwargs,
        ):
            nonlocal active, max_active
            assert underlying_asset == "NBIS"
            assert client is not None
            active += 1
            max_active = max(max_active, active)
            seen_tickers.append(option_ticker_name)
            await asyncio.sleep(0)
            active -= 1
            if option_ticker_name == "O:NBIS2":
                return None
            return f"snapshot:{option_ticker_name}"

    monkeypatch.setattr(option_api, "Fetcher", _FakeFetcher)
    monkeypatch.setattr(option_api, "_build_snapshot_async_client", lambda timeout: _FakeClient())
    monkeypatch.setattr(option_api, "SNAPSHOT_FETCH_BATCH_SIZE", 2)
    monkeypatch.setattr(option_api, "SNAPSHOT_FETCH_CONCURRENCY", 1)

    results = await option_api.fetch_snapshots_batch(contracts)

    assert results == [
        "snapshot:O:NBIS1",
        None,
        "snapshot:O:NBIS3",
    ]
    assert seen_tickers == ["O:NBIS1", "O:NBIS2", "O:NBIS3"]
    assert max_active == 1


@pytest.mark.asyncio
async def test_fetch_snapshots_batch_preserves_length_on_unexpected_fetch_error(monkeypatch):
    class _FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    contracts = [
        MagicMock(underlying_ticker="NBIS", ticker="O:NBIS1"),
        MagicMock(underlying_ticker="NBIS", ticker="O:NBIS2"),
    ]

    class _FakeFetcher:
        def __init__(self, _asset):
            pass

        async def fetch_daily_snapshot_async(
            self,
            underlying_asset,
            option_ticker_name,
            *args,
            client=None,
            **kwargs,
        ):
            if option_ticker_name == "O:NBIS2":
                raise RuntimeError("bad payload")
            return f"snapshot:{option_ticker_name}"

    monkeypatch.setattr(option_api, "Fetcher", _FakeFetcher)
    monkeypatch.setattr(option_api, "_build_snapshot_async_client", lambda timeout: _FakeClient())
    monkeypatch.setattr(option_api, "SNAPSHOT_FETCH_BATCH_SIZE", 2)

    results = await option_api.fetch_snapshots_batch(contracts)

    assert results == ["snapshot:O:NBIS1", None]


@pytest.mark.asyncio
async def test_fetch_chain_snapshots_for_underlying_uses_sdk_pagination(monkeypatch):
    snapshot_a = MagicMock()
    snapshot_b = MagicMock()

    class _FakeFetcher:
        def __init__(self, asset):
            assert asset == "NBIS"

        def get_chain_snapshots(self):
            return [snapshot_a, snapshot_b]

    monkeypatch.setattr(option_api, "Fetcher", _FakeFetcher)

    results = await option_api.fetch_chain_snapshots_for_underlying("NBIS")

    assert results == [snapshot_a, snapshot_b]


@pytest.mark.asyncio
async def test_fetch_daily_snapshot_async_redacts_api_key_in_timeout_logs(monkeypatch, caplog):
    class _FakeClient:
        async def get(self, url):
            raise httpx.ConnectTimeout("timeout")

    monkeypatch.setenv("POLYGON_API_KEY", "super-secret-key")
    fetcher = option_api.Fetcher(None)

    with caplog.at_level("ERROR"):
        result = await fetcher.fetch_daily_snapshot_async(
            "NBIS",
            "O:NBIS260918P00080000",
            client=_FakeClient(),
            connect_timeout=10.0,
        )

    assert result is None
    assert "super-secret-key" not in caplog.text
    assert "apiKey=%5BREDACTED%5D" in caplog.text


@pytest.mark.asyncio
async def test_fetch_daily_snapshot_async_retries_read_timeout(monkeypatch):
    class _FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "results": {
                    "break_even_price": 1.0,
                    "day": {
                        "change": 0.0,
                        "change_percent": 0.0,
                        "close": 1.0,
                        "high": 1.0,
                        "last_updated": 1,
                        "low": 1.0,
                        "open": 1.0,
                        "previous_close": 1.0,
                        "volume": 1,
                        "vwap": 1.0,
                    },
                    "details": {"ticker": "O:NBIS260918P00080000"},
                    "greeks": {"delta": 0.1, "gamma": 0.1, "theta": -0.1, "vega": 0.1},
                    "implied_volatility": 0.2,
                    "market_status": "open",
                    "open_interest": 1,
                    "underlying_asset": {"price": 1.0, "ticker": "NBIS"},
                }
            }

    class _FakeClient:
        def __init__(self):
            self.calls = 0

        async def get(self, url):
            self.calls += 1
            if self.calls == 1:
                raise httpx.ReadTimeout("timeout")
            return _FakeResponse()

    monkeypatch.setenv("POLYGON_API_KEY", "super-secret-key")
    fetcher = option_api.Fetcher(None)
    client = _FakeClient()

    with patch("microservices.option_ingestor.api.asyncio.sleep", new=AsyncMock()) as mock_sleep:
        result = await fetcher.fetch_daily_snapshot_async(
            "NBIS",
            "O:NBIS260918P00080000",
            client=client,
            read_timeout=10.0,
            max_retries=3,
            base_delay_seconds=0.5,
        )

    assert result is not None
    assert client.calls == EXPECTED_RETRY_FETCH_CALLS
    mock_sleep.assert_awaited_once()


@pytest.mark.asyncio
async def test_fetch_daily_snapshot_async_does_not_retry_non_timeout_request_error(monkeypatch):
    class _FakeClient:
        def __init__(self):
            self.calls = 0

        async def get(self, url):
            self.calls += 1
            request = httpx.Request("GET", url)
            raise httpx.NetworkError("boom", request=request)

    monkeypatch.setenv("POLYGON_API_KEY", "super-secret-key")
    fetcher = option_api.Fetcher(None)
    client = _FakeClient()

    with patch("microservices.option_ingestor.api.asyncio.sleep", new=AsyncMock()) as mock_sleep:
        result = await fetcher.fetch_daily_snapshot_async(
            "NBIS",
            "O:NBIS260918P00080000",
            client=client,
            max_retries=3,
            base_delay_seconds=0.5,
        )

    assert result is None
    assert client.calls == 1
    mock_sleep.assert_not_awaited()


@pytest.mark.asyncio
async def test_upsert_option_contract_success(ingestor):
    contract = OptionsContract.from_dict(
        {
            "ticker": "TST",
            "underlying_ticker": "TST",
            "strike_price": 100.0,
            "expiration_date": "2025-12-31",
            "contract_type": "call",
        }
    )

    with patch("prisma.models.Options.prisma") as mock_prisma:
        mock_prisma.return_value.upsert = AsyncMock(return_value="mocked")
        result = await ingestor._upsert_option_contract(contract)
        assert result == "mocked"


@pytest.mark.asyncio
async def test_upsert_option_contract_retries_transient_db_error(ingestor):
    contract = OptionsContract.from_dict(
        {
            "ticker": "TST",
            "underlying_ticker": "TST",
            "strike_price": 100.0,
            "expiration_date": "2025-12-31",
            "contract_type": "call",
        }
    )

    class DataError(Exception):
        pass

    with (
        patch("prisma.models.Options.prisma") as mock_prisma,
        patch(
            "microservices.option_ingestor.ingestor.asyncio.sleep", new=AsyncMock()
        ) as mock_sleep,
    ):
        mock_prisma.return_value.upsert = AsyncMock(
            side_effect=[
                DataError("P1001 Can't reach database server"),
                "mocked",
            ]
        )
        result = await ingestor._upsert_option_contract(contract)
        assert result == "mocked"
        assert mock_prisma.return_value.upsert.await_count == EXPECTED_RETRY_UPSERT_CALLS
        mock_sleep.assert_awaited_once()


@pytest.mark.asyncio
async def test_upsert_option_contract_error(ingestor):
    contract = OptionsContract.from_dict(
        {
            "ticker": "TST",
            "underlying_ticker": "TST",
            "strike_price": 100.0,
            "expiration_date": "2025-12-31",
            "contract_type": "call",
        }
    )
    with patch("prisma.models.Options.prisma") as mock_prisma:
        mock_prisma.return_value.upsert = AsyncMock(side_effect=RuntimeError("fail"))
        with pytest.raises(RuntimeError):
            await ingestor._upsert_option_contract(contract)


@pytest.mark.asyncio
async def test_upsert_option_snapshot_ticker_never_active(snapshots_ingestor):
    with patch("prisma.models.OptionSnapshot.prisma") as mock_prisma:
        mock_prisma.return_value.upsert = AsyncMock(side_effect=OptionTickerNeverActiveError)
        snapshot = MagicMock()
        snapshot.day = MagicMock()
        snapshot.greeks = None
        await snapshots_ingestor._upsert_option_snapshot("TST", snapshot)


@pytest.mark.asyncio
async def test_upsert_option_snapshot_retries_client_not_connected(snapshots_ingestor):
    snapshot = MagicMock()
    snapshot.day = MagicMock(last_updated=1, volume=1, close=1.0, open=1.0, change_percent=0.0)
    snapshot.greeks = None
    snapshot.open_interest = 1
    snapshot.implied_volatility = 0.1

    with (
        patch("prisma.models.OptionSnapshot.prisma") as mock_prisma,
        patch(
            "microservices.snapshot_ingestor.ingestor.asyncio.sleep", new=AsyncMock()
        ) as mock_sleep,
        patch("microservices.snapshot_ingestor.ingestor.ns_to_datetime", return_value="dt"),
    ):
        mock_prisma.return_value.upsert = AsyncMock(
            side_effect=[ClientNotConnectedError("not connected"), "mocked"]
        )
        result = await snapshots_ingestor._upsert_option_snapshot("TST", snapshot)
        assert result == "mocked"
        assert mock_prisma.return_value.upsert.await_count == EXPECTED_RETRY_UPSERT_CALLS
        mock_sleep.assert_awaited_once()


def test_build_snapshot_upsert_payload_includes_underlying_price():
    snapshot = MagicMock()
    snapshot.day = MagicMock(volume=1, close=1.0, open=0.9, change_percent=0.1)
    snapshot.greeks = None
    snapshot.open_interest = 1
    snapshot.implied_volatility = 0.1
    snapshot.underlying_asset = MagicMock(price=123.45)

    payload = _build_snapshot_upsert_payload(
        contract_ticker="TST",
        snapshot=snapshot,
        last_updated_dt="dt",
        curr_datetime="now",
        greeks=None,
    )

    assert payload["create"]["underlying_price"] == 123.45
    assert payload["update"]["underlying_price"] == 123.45


@pytest.mark.asyncio
async def test_upsert_option_snapshot_does_not_retry_non_transient_error(snapshots_ingestor):
    snapshot = MagicMock()
    snapshot.day = MagicMock(last_updated=1, volume=1, close=1.0, open=1.0, change_percent=0.0)
    snapshot.greeks = None
    snapshot.open_interest = 1
    snapshot.implied_volatility = 0.1

    with (
        patch("prisma.models.OptionSnapshot.prisma") as mock_prisma,
        patch(
            "microservices.snapshot_ingestor.ingestor.asyncio.sleep", new=AsyncMock()
        ) as mock_sleep,
        patch("microservices.snapshot_ingestor.ingestor.ns_to_datetime", return_value="dt"),
    ):
        mock_prisma.return_value.upsert = AsyncMock(side_effect=RuntimeError("fail"))
        result = await snapshots_ingestor._upsert_option_snapshot("TST", snapshot)
        assert result is None
        assert mock_prisma.return_value.upsert.await_count == 1
        mock_sleep.assert_not_awaited()


def test_option_ingestor_requires_retriever():
    with pytest.raises(ValueError):
        OptionIngestor(option_retriever=None)


def test_option_snapshots_ingestor_requires_retriever():
    with pytest.raises(ValueError):
        OptionSnapshotsIngestor(option_retriever=None)
