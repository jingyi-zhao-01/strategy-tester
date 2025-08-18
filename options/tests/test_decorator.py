import asyncio
import types

# Provide a lightweight mock Prisma client for decorator usage in tests
class _MockPrisma:
    async def connect(self):
        pass

    async def disconnect(self):
        pass

# Inject mock db before importing decorator
import options.decorator as decorator
if decorator.db is None:
    decorator.db = _MockPrisma()


import pytest

from options.decorator import bounded_async_sem, bounded_db_connection


@pytest.mark.asyncio
async def test_bounded_db_connection_and_semaphore(monkeypatch):
    open_calls = []
    close_calls = []
    concurrent = 0
    max_concurrent = 0

    class MockPrisma:
        async def connect(self):
            open_calls.append(1)

        async def disconnect(self):
            close_calls.append(1)

    # Patch db in the decorator's closure
    monkeypatch.setattr("options.decorator.db", MockPrisma())

    @bounded_async_sem(limit=2)
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
    assert max_concurrent == 2  # noqa: PLR2004
    assert len(open_calls) == 1
    assert len(close_calls) == 1
