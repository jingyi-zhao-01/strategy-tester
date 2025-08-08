from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from options.ingestor import OptionIngestor, OptionTickerNeverActiveError
from options.models import OptionIngestParams, OptionsContract


@pytest.fixture
def mock_option_retriever():
    mock = MagicMock()
    mock.with_ingest_time.return_value = mock

    async def empty_async_gen():
        if False:
            yield

    mock.stream_retrieve = empty_async_gen
    return mock


@pytest.fixture
def ingestor(mock_option_retriever):
    return OptionIngestor(option_retriever=mock_option_retriever)


@pytest.mark.asyncio
async def test_ingest_options_empty(monkeypatch, ingestor):
    monkeypatch.setattr(
        "options.api.options.Fetcher",
        lambda asset: MagicMock(get_call_contracts=lambda: [], get_put_contracts=lambda: []),
    )
    monkeypatch.setattr(
        "options.api.options.get_contract_within_price_range", lambda contracts, price, year: []
    )
    await ingestor.ingest_options([OptionIngestParams("TEST", (0, 1), (2025, 2025))])


@pytest.mark.asyncio
async def test_ingest_option_snapshots_empty(ingestor):
    await ingestor.ingest_option_snapshots()


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
        mock_prisma.return_value.upsert = AsyncMock(side_effect=Exception("fail"))
        with pytest.raises(Exception):  # noqa: B017
            await ingestor._upsert_option_contract(contract)


@pytest.mark.asyncio
async def test_upsert_option_snapshot_ticker_never_active(ingestor):
    with patch("prisma.models.OptionSnapshot.prisma") as mock_prisma:
        mock_prisma.return_value.upsert = AsyncMock(side_effect=OptionTickerNeverActiveError)
        snapshot = MagicMock()
        snapshot.day = MagicMock()
        snapshot.greeks = None
        await ingestor._upsert_option_snapshot("TST", snapshot)


def test_option_ingestor_requires_retriever():
    with pytest.raises(ValueError):
        OptionIngestor(option_retriever=None)


# @pytest.mark.asyncio
# async def test_upsert_option_snapshot_unique_violation(ingestor):
#     with patch("prisma.models.OptionSnapshot.prisma") as mock_prisma:
#         mock_prisma.return_value.upsert = AsyncMock(side_effect=UniqueViolationError)
#         snapshot = MagicMock()
#         snapshot.day = MagicMock()
#         snapshot.greeks = None
#         await ingestor._upsert_option_snapshot("TST", snapshot)
