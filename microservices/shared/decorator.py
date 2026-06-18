import asyncio
import functools
import logging
import os
from importlib import import_module

from opentelemetry.trace import SpanKind

from microservices.shared.errors import is_retryable_db_error
from microservices.shared.observability import annotate_span_error, start_span_sync

CONCURRENCY_LIMIT = int(os.getenv("INGEST_CONCURRENCY_LIMIT", "200"))
DATA_BASE_CONCURRENCY_LIMIT = int(os.getenv("INGEST_DB_CONCURRENCY_LIMIT", "10"))
OPTION_BATCH_RETRIEVAL_SIZE = int(os.getenv("INGEST_OPTION_BATCH_SIZE", "500"))
DB_CONNECT_MAX_ATTEMPTS = int(os.getenv("INGEST_DB_CONNECT_MAX_ATTEMPTS", "3"))
DB_CONNECT_BASE_DELAY_SECONDS = float(os.getenv("INGEST_DB_CONNECT_BASE_DELAY_SECONDS", "0.5"))
_db_semaphore = asyncio.Semaphore(DATA_BASE_CONCURRENCY_LIMIT)
logger = logging.getLogger(__name__)

semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

_prisma_module = import_module("prisma")
Prisma = _prisma_module.Prisma
db = Prisma(auto_register=True)
_db_connected = False
_db_lock = asyncio.Lock()


async def connect_db() -> None:
    global _db_connected  # noqa: PLW0603
    async with _db_lock:
        if not _db_connected:
            for attempt in range(1, DB_CONNECT_MAX_ATTEMPTS + 1):
                try:
                    await db.connect()
                    _db_connected = True
                    _log_connection_pool_stats()
                    return
                except Exception as exc:
                    if not is_retryable_db_error(exc) or attempt >= DB_CONNECT_MAX_ATTEMPTS:
                        raise

                    delay = DB_CONNECT_BASE_DELAY_SECONDS * (2 ** (attempt - 1))
                    logger.warning(
                        "Retrying initial database connection after transient error in %.2fs "
                        "(attempt %s/%s): %s",
                        delay,
                        attempt,
                        DB_CONNECT_MAX_ATTEMPTS,
                        exc,
                    )
                    await asyncio.sleep(delay)


async def disconnect_db() -> None:
    global _db_connected  # noqa: PLW0603
    async with _db_lock:
        if _db_connected:
            await db.disconnect()
            _db_connected = False


def bounded_db_connection(func):
    async def wrapper(*args, **kwargs):
        async with _db_semaphore:
            _log_connection_pool_stats()
            return await func(*args, **kwargs)

    return wrapper


def bounded_db_connection_asyncgen(func):
    async def wrapper(*args, **kwargs):
        iterator = func(*args, **kwargs)
        try:
            async for item in iterator:
                async with _db_semaphore:
                    _log_connection_pool_stats()
                    yield item
        finally:
            aclose = getattr(iterator, "aclose", None)
            if aclose is not None:
                await aclose()

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
                logger.info(
                    "Database pool stats - Active: %s, Min: %s, Max: %s",
                    active_conns,
                    min_size,
                    max_size,
                )
    except Exception as e:
        logger.debug("Could not retrieve connection pool stats: %s", e)


def bounded_async_sem(limit=CONCURRENCY_LIMIT):
    sem = asyncio.Semaphore(limit) if limit else semaphore

    def wrapper(coro):
        async def inner(*args, **kwargs):
            async with sem:
                return await coro(*args, **kwargs)

        return inner

    return wrapper


def traced_span_async(name: str, attributes: dict | None = None, kind=None):
    _ = (name, attributes, kind)

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            with start_span_sync(
                name,
                kind=kind or SpanKind.INTERNAL,
                attributes=attributes,
            ) as span:
                try:
                    return await func(*args, **kwargs)
                except Exception as exc:
                    annotate_span_error(span, exc)
                    raise

        return wrapper

    return decorator


def traced_span_sync(name: str, attributes: dict | None = None, kind=None):
    _ = (name, attributes, kind)

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with start_span_sync(
                name,
                kind=kind or SpanKind.INTERNAL,
                attributes=attributes,
            ) as span:
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    annotate_span_error(span, exc)
                    raise

        return wrapper

    return decorator


def traced_span_asyncgen(name: str | None = None, attributes: dict | None = None, kind=None):
    _ = (name, attributes, kind)

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            iterator = func(*args, **kwargs)
            with start_span_sync(
                name or func.__name__,
                kind=kind or SpanKind.INTERNAL,
                attributes=attributes,
            ) as span:
                try:
                    async for item in iterator:
                        yield item
                except BaseException as exc:
                    if isinstance(exc, GeneratorExit | asyncio.CancelledError):
                        raise
                    annotate_span_error(span, exc)
                    raise
                finally:
                    aclose = getattr(iterator, "aclose", None)
                    if aclose is not None:
                        await aclose()

        return wrapper

    return decorator
