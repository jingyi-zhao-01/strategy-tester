import asyncio

import pytest

from microservices.shared import decorator
from microservices.shared.decorator import (
    bounded_async_sem,
    bounded_db_connection,
    bounded_db_connection_asyncgen,
    connect_db,
    disconnect_db,
    traced_span_asyncgen,
)

EXPECTED_MAX_CONCURRENCY = 2


class _MockPrisma:
    async def connect(self):
        # Intentional async no-op for test double behavior.
        await asyncio.sleep(0)

    async def disconnect(self):
        # Intentional async no-op for test double behavior.
        await asyncio.sleep(0)


decorator.db = _MockPrisma()


@pytest.mark.asyncio
async def test_connect_db_and_disconnect_db(monkeypatch):
    open_calls = []
    close_calls = []

    class MockPrisma:
        async def connect(self):
            await asyncio.sleep(0)
            open_calls.append(1)

        async def disconnect(self):
            await asyncio.sleep(0)
            close_calls.append(1)

    monkeypatch.setattr("microservices.shared.decorator.db", MockPrisma())
    monkeypatch.setattr("microservices.shared.decorator._db_connected", False)

    await connect_db()
    await connect_db()
    await disconnect_db()
    await disconnect_db()

    assert len(open_calls) == 1
    assert len(close_calls) == 1


@pytest.mark.asyncio
async def test_bounded_db_connection_and_semaphore():
    concurrent = 0
    max_concurrent = 0

    @bounded_async_sem(limit=EXPECTED_MAX_CONCURRENCY)
    async def coroutine_task(i, delay=0.1):
        nonlocal concurrent, max_concurrent
        concurrent += 1
        max_concurrent = max(max_concurrent, concurrent)
        await asyncio.sleep(delay)
        concurrent -= 1
        return i

    @bounded_db_connection
    async def batch_task():
        results = await asyncio.gather(*(coroutine_task(i) for i in range(5)))
        return results

    results = await batch_task()
    assert sorted(results) == list(range(5))
    assert max_concurrent == EXPECTED_MAX_CONCURRENCY


@pytest.mark.asyncio
async def test_asyncgen_decorators_allow_early_close_without_error():
    yielded = []
    closed = False

    @traced_span_asyncgen(name="test_asyncgen")
    @bounded_db_connection_asyncgen
    async def sample_generator():
        nonlocal closed
        try:
            yield 1
            yield 2
        finally:
            closed = True

    iterator = sample_generator()
    first = await anext(iterator)
    yielded.append(first)
    await iterator.aclose()

    assert yielded == [1]
    assert closed is True
