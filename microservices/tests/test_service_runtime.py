from unittest.mock import AsyncMock, MagicMock

import pytest

from microservices.option_ingestor.service import _run_job as run_option_job
from microservices.snapshot_ingestor.service import _run_job as run_snapshot_job


@pytest.mark.asyncio
async def test_option_run_job_uses_job_scoped_db_lifecycle(monkeypatch):
    connect = AsyncMock()
    disconnect = AsyncMock()
    ingestor = MagicMock()
    ingestor.ingest_options = AsyncMock()
    targets = [MagicMock()]

    monkeypatch.setattr("microservices.option_ingestor.service.connect_db", connect)
    monkeypatch.setattr("microservices.option_ingestor.service.disconnect_db", disconnect)

    await run_option_job(ingestor=ingestor, targets=targets)

    connect.assert_awaited_once()
    ingestor.ingest_options.assert_awaited_once_with(underlying_assets=targets)
    disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_option_run_job_disconnects_on_failure(monkeypatch):
    connect = AsyncMock()
    disconnect = AsyncMock()
    ingestor = MagicMock()
    ingestor.ingest_options = AsyncMock(side_effect=RuntimeError("boom"))

    monkeypatch.setattr("microservices.option_ingestor.service.connect_db", connect)
    monkeypatch.setattr("microservices.option_ingestor.service.disconnect_db", disconnect)

    with pytest.raises(RuntimeError, match="boom"):
        await run_option_job(ingestor=ingestor, targets=[])

    connect.assert_awaited_once()
    disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_snapshot_run_job_uses_job_scoped_db_lifecycle(monkeypatch):
    connect = AsyncMock()
    disconnect = AsyncMock()
    ingestor = MagicMock()
    ingestor.ingest_option_snapshots = AsyncMock()

    monkeypatch.setattr("microservices.snapshot_ingestor.service.connect_db", connect)
    monkeypatch.setattr("microservices.snapshot_ingestor.service.disconnect_db", disconnect)

    await run_snapshot_job(ingestor=ingestor)

    connect.assert_awaited_once()
    ingestor.ingest_option_snapshots.assert_awaited_once_with()
    disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_snapshot_run_job_disconnects_on_failure(monkeypatch):
    connect = AsyncMock()
    disconnect = AsyncMock()
    ingestor = MagicMock()
    ingestor.ingest_option_snapshots = AsyncMock(side_effect=RuntimeError("boom"))

    monkeypatch.setattr("microservices.snapshot_ingestor.service.connect_db", connect)
    monkeypatch.setattr("microservices.snapshot_ingestor.service.disconnect_db", disconnect)

    with pytest.raises(RuntimeError, match="boom"):
        await run_snapshot_job(ingestor=ingestor)

    connect.assert_awaited_once()
    disconnect.assert_awaited_once()
