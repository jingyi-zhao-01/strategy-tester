from unittest.mock import AsyncMock, MagicMock

import pytest

from microservices.option_ingestor.service import _run_job as run_option_job
from microservices.option_ingestor.service import run as run_option_service
from microservices.snapshot_ingestor.service import _run_job as run_snapshot_job
from microservices.snapshot_ingestor.service import run as run_snapshot_service


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


def test_option_service_flushes_tracing_on_exit(monkeypatch):
    load_env = MagicMock()
    initialize = MagicMock()
    shutdown = MagicMock()
    configure_logger = MagicMock()
    async_run = MagicMock(side_effect=lambda coro: coro.close())
    retriever = MagicMock()
    ingestor = MagicMock()

    monkeypatch.setattr("microservices.option_ingestor.service.load_env", load_env)
    monkeypatch.setattr(
        "microservices.option_ingestor.service.get_option_runtime_config",
        lambda: MagicMock(service_name="option-ingestor"),
    )
    monkeypatch.setattr(
        "microservices.option_ingestor.service.get_retriever_config",
        lambda: MagicMock(concurrency_limit=1, batch_size=1),
    )
    monkeypatch.setattr(
        "microservices.option_ingestor.service.get_option_targets_from_env",
        lambda: [],
    )
    monkeypatch.setattr("microservices.option_ingestor.service.initialize_tracing", initialize)
    monkeypatch.setattr("microservices.option_ingestor.service.shutdown_tracing", shutdown)
    monkeypatch.setattr("microservices.option_ingestor.service._configure_logging", configure_logger)
    monkeypatch.setattr("microservices.option_ingestor.service.OptionRetriever", lambda **kwargs: retriever)
    monkeypatch.setattr(
        "microservices.option_ingestor.service.OptionIngestor",
        lambda option_retriever: ingestor,
    )
    monkeypatch.setattr("microservices.option_ingestor.service.asyncio.run", async_run)

    run_option_service()

    load_env.assert_called_once()
    initialize.assert_called_once_with("option-ingestor")
    async_run.assert_called_once()
    shutdown.assert_called_once()


def test_snapshot_service_flushes_tracing_on_exit(monkeypatch):
    load_env = MagicMock()
    initialize = MagicMock()
    shutdown = MagicMock()
    configure_logger = MagicMock()
    async_run = MagicMock(side_effect=lambda coro: coro.close())
    retriever = MagicMock()
    ingestor = MagicMock()

    monkeypatch.setattr("microservices.snapshot_ingestor.service.load_env", load_env)
    monkeypatch.setattr(
        "microservices.snapshot_ingestor.service.get_snapshot_runtime_config",
        lambda: MagicMock(service_name="snapshot-ingestor"),
    )
    monkeypatch.setattr(
        "microservices.snapshot_ingestor.service.get_retriever_config",
        lambda: MagicMock(concurrency_limit=1, batch_size=1),
    )
    monkeypatch.setattr(
        "microservices.snapshot_ingestor.service.initialize_tracing",
        initialize,
    )
    monkeypatch.setattr("microservices.snapshot_ingestor.service.shutdown_tracing", shutdown)
    monkeypatch.setattr(
        "microservices.snapshot_ingestor.service._configure_logging",
        configure_logger,
    )
    monkeypatch.setattr(
        "microservices.snapshot_ingestor.service.OptionRetriever",
        lambda **kwargs: retriever,
    )
    monkeypatch.setattr(
        "microservices.snapshot_ingestor.service.OptionSnapshotsIngestor",
        lambda option_retriever: ingestor,
    )
    monkeypatch.setattr("microservices.snapshot_ingestor.service.asyncio.run", async_run)

    run_snapshot_service()

    load_env.assert_called_once()
    initialize.assert_called_once_with("snapshot-ingestor")
    async_run.assert_called_once()
    shutdown.assert_called_once()
