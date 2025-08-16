from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from options.retriever import OptionRetriever


@pytest.fixture
def retriever():
    retriever = OptionRetriever(batch_size=1)
    return retriever


@pytest.mark.asyncio
async def test_with_ingest_time_sets_value(retriever):
    retriever.with_ingest_time("2025-01-01T00:00:00Z")
    assert retriever.ingest_time == "2025-01-01T00:00:00Z"


@pytest.mark.asyncio
async def test_ingest_time_raises_if_not_set():
    r = OptionRetriever(batch_size=1)
    with pytest.raises(ValueError):
        _ = r.ingest_time


@pytest.mark.asyncio
async def test_retrieve_all_success(monkeypatch, retriever):
    mock_contracts = [MagicMock(), MagicMock()]
    with patch("prisma.models.Options.prisma") as mock_prisma:
        mock_prisma.return_value.find_many = AsyncMock(return_value=mock_contracts)
        retriever.with_ingest_time("2025-01-01T00:00:00Z")
        result = await retriever.retrieve_all()
        assert result == mock_contracts


@pytest.mark.asyncio
async def test_retrieve_all_error(monkeypatch, retriever):
    with patch("prisma.models.Options.prisma") as mock_prisma:
        mock_prisma.return_value.find_many = AsyncMock(side_effect=Exception("fail"))
        retriever.with_ingest_time("2025-01-01T00:00:00Z")
        result = await retriever.retrieve_all()
        assert result == []


@pytest.mark.asyncio
async def test_stream_retrieve(monkeypatch, retriever):
    batch1 = [MagicMock()]
    batch2 = [MagicMock()]
    batch3 = [MagicMock()]

    async def fake_find_many(**kwargs):
        if fake_find_many.counter == 0:
            fake_find_many.counter += 1
            return batch1
        elif fake_find_many.counter == 1:
            fake_find_many.counter += 1
            return batch2
        elif fake_find_many.counter == 2:  # noqa: PLR2004
            fake_find_many.counter += 1
            return batch3
        else:
            return []

    fake_find_many.counter = 0
    with patch("prisma.models.Options.prisma") as mock_prisma:
        mock_prisma.return_value.find_many = AsyncMock(side_effect=fake_find_many)
        retriever.with_ingest_time("2025-01-01T00:00:00Z")
        batches = []
        async for batch in retriever.stream_retrieve_active():
            batches.append(batch)
        assert batches == [batch1, batch2, batch3]


@pytest.mark.asyncio
async def test_stream_retrieve_error(monkeypatch, retriever):
    with patch("prisma.models.Options.prisma") as mock_prisma:
        mock_prisma.return_value.find_many = AsyncMock(side_effect=Exception("fail"))
        retriever.with_ingest_time("2025-01-01T00:00:00Z")
        batches = []
        async for batch in retriever.stream_retrieve_active():
            batches.append(batch)
        assert batches == []
