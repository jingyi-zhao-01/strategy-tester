from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from microservices.option_ingestor.ingestor import OptionIngestor
from microservices.shared.errors import OptionTickerNeverActiveError
from microservices.shared.models import OptionIngestParams, OptionsContract
from microservices.snapshot_ingestor.ingestor import OptionSnapshotsIngestor


@pytest.fixture
def mock_option_retriever():
    mock = MagicMock()
    mock.with_ingest_time.return_value = mock

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
        patch("microservices.option_ingestor.ingestor.asyncio.sleep", new=AsyncMock()) as mock_sleep,
    ):
        mock_prisma.return_value.upsert = AsyncMock(
            side_effect=[
                DataError("P1001 Can't reach database server"),
                "mocked",
            ]
        )
        result = await ingestor._upsert_option_contract(contract)
        assert result == "mocked"
        assert mock_prisma.return_value.upsert.await_count == 2
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
    from prisma.errors import ClientNotConnectedError

    snapshot = MagicMock()
    snapshot.day = MagicMock(last_updated=1, volume=1, close=1.0, open=1.0, change_percent=0.0)
    snapshot.greeks = None
    snapshot.open_interest = 1
    snapshot.implied_volatility = 0.1

    with (
        patch("prisma.models.OptionSnapshot.prisma") as mock_prisma,
        patch("microservices.snapshot_ingestor.ingestor.asyncio.sleep", new=AsyncMock()) as mock_sleep,
        patch("microservices.snapshot_ingestor.ingestor.ns_to_datetime", return_value="dt"),
    ):
        mock_prisma.return_value.upsert = AsyncMock(
            side_effect=[ClientNotConnectedError("not connected"), "mocked"]
        )
        result = await snapshots_ingestor._upsert_option_snapshot("TST", snapshot)
        assert result == "mocked"
        assert mock_prisma.return_value.upsert.await_count == 2
        mock_sleep.assert_awaited_once()


def test_option_ingestor_requires_retriever():
    with pytest.raises(ValueError):
        OptionIngestor(option_retriever=None)


def test_option_snapshots_ingestor_requires_retriever():
    with pytest.raises(ValueError):
        OptionSnapshotsIngestor(option_retriever=None)
