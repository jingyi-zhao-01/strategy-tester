import asyncio
import contextlib
import os
from importlib import import_module

from opentelemetry import trace
from opentelemetry.trace import SpanKind

from lib.observability.log import Log

CONCURRENCY_LIMIT = int(os.getenv("INGEST_CONCURRENCY_LIMIT", "200"))
DATA_BASE_CONCURRENCY_LIMIT = int(os.getenv("INGEST_DB_CONCURRENCY_LIMIT", "10"))
OPTION_BATCH_RETRIEVAL_SIZE = int(os.getenv("INGEST_OPTION_BATCH_SIZE", "500"))
_db_semaphore = asyncio.Semaphore(DATA_BASE_CONCURRENCY_LIMIT)

tracer = trace.get_tracer(__name__)

semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

_prisma_module = import_module("prisma")
Prisma = _prisma_module.Prisma
db = Prisma(auto_register=True)
_db_connected = False
_db_lock = asyncio.Lock()


async def _ensure_db_connected(client) -> bool:
    global _db_connected  # noqa: PLW0603
    did_connect = False
    async with _db_lock:
        if not _db_connected:
            await client.connect()
            _db_connected = True
            did_connect = True
            _log_connection_pool_stats()
    return did_connect


async def _close_db_if_open(client, should_close: bool) -> None:
    global _db_connected  # noqa: PLW0603
    if should_close:
        await client.disconnect()
        _db_connected = False


def bounded_db_connection(func):
    async def wrapper(*args, **kwargs):
        client = db
        if client is not None and hasattr(client, "connect") and hasattr(client, "disconnect"):
            did_connect = await _ensure_db_connected(client)
            try:
                async with _db_semaphore:
                    _log_connection_pool_stats()
                    return await func(*args, **kwargs)
            finally:
                await _close_db_if_open(client, should_close=did_connect)
        return await func(*args, **kwargs)

    return wrapper


def bounded_db_connection_asyncgen(func):
    async def wrapper(*args, **kwargs):
        client = db
        if client is not None and hasattr(client, "connect") and hasattr(client, "disconnect"):
            did_connect = await _ensure_db_connected(client)
            try:
                async for item in func(*args, **kwargs):
                    async with _db_semaphore:
                        _log_connection_pool_stats()
                        yield item
            finally:
                await _close_db_if_open(client, should_close=did_connect)
            return

        async for item in func(*args, **kwargs):
            yield item

    return wrapper


def _log_connection_pool_stats():
    try:
        engine = getattr(db, "_engine", None)  # type: ignore[attr-defined]
        if engine and hasattr(engine, "_pool"):
            pool = engine._pool
            if pool:
                active_conns = len(pool._holders) if hasattr(pool, "_holders") else "unknown"
                min_size = pool._minsize if hasattr(pool, "_minsize") else "unknown"
                max_size = pool._maxsize if hasattr(pool, "_maxsize") else "unknown"
                Log.log_db_connection_pool_stats(active_conns, min_size, max_size)
    except Exception as e:
        Log.debug(f"Could not retrieve connection pool stats: {e}")


def bounded_async_sem(limit=CONCURRENCY_LIMIT):
    sem = asyncio.Semaphore(limit) if limit else semaphore

    def wrapper(coro):
        async def inner(*args, **kwargs):
            async with sem:
                return await coro(*args, **kwargs)

        return inner

    return wrapper


def traced_span_async(
    name: str, attributes: dict | None = None, kind: SpanKind = SpanKind.INTERNAL
):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            with tracer.start_as_current_span(name, kind=kind) as span:
                if attributes:
                    for k, v in attributes.items():
                        with contextlib.suppress(Exception):
                            span.set_attribute(k, v)
                return await func(*args, **kwargs)

        return wrapper

    return decorator


def traced_span_sync(name: str, attributes: dict | None = None, kind: SpanKind = SpanKind.INTERNAL):
    def decorator(func):
        def wrapper(*args, **kwargs):
            with tracer.start_as_current_span(name, kind=kind) as span:
                if attributes:
                    for k, v in attributes.items():
                        with contextlib.suppress(Exception):
                            span.set_attribute(k, v)

                return func(*args, **kwargs)

        return wrapper

    return decorator


def traced_span_asyncgen(
    name: str | None = None, attributes: dict | None = None, kind: SpanKind = SpanKind.CLIENT
):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            span_name = name or f"{func.__module__}.{func.__name__}"
            with tracer.start_as_current_span(span_name, kind=kind) as span:
                if attributes:
                    for k, v in attributes.items():
                        with contextlib.suppress(Exception):
                            span.set_attribute(k, v)
                async for item in func(*args, **kwargs):
                    yield item

        return wrapper

    return decorator
