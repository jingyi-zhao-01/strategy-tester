import asyncio
import contextlib

from dotenv import load_dotenv
from opentelemetry import trace
from opentelemetry.trace import SpanKind

from lib.observability.log import Log
from prisma import Prisma

load_dotenv()

CONCURRENCY_LIMIT = 200
DATA_BASE_CONCURRENCY_LIMIT = 10
OPTION_BATCH_RETRIEVAL_SIZE = 500
_db_semaphore = asyncio.Semaphore(DATA_BASE_CONCURRENCY_LIMIT)

# SystemMetricsInstrumentor().instrument()
# tracer = trace.get_tracer("polygon")
tracer = trace.get_tracer(__name__)

semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

db = Prisma(auto_register=True)
_db_connected = False
_db_lock = asyncio.Lock()


def bounded_db_connection(func):
    async def wrapper(*args, **kwargs):
        global _db_connected  # noqa: PLW0603
        client = db
        if client is not None and hasattr(client, "connect") and hasattr(client, "disconnect"):
            # Only connect once, reuse the connection
            async with _db_lock:
                if not _db_connected:
                    try:
                        # Log.debug("Prisma connect() sees DATABASE_URL = %s",
                        #  os.getenv("DATABASE_URL"))
                        await client.connect()
                        _db_connected = True
                        # Log pool info after connection
                        _log_connection_pool_stats()
                    except Exception:
                        # Log.debug("Prisma connect() failed: %s", e)
                        raise
            # Limit concurrent DB operations to the connection pool size
            # This prevents overwhelming the database connection pool
            async with _db_semaphore:
                # Log connection stats before each operation
                _log_connection_pool_stats()
                return await func(*args, **kwargs)
        else:
            return await func(*args, **kwargs)

    return wrapper


def bounded_db_connection_asyncgen(func):
    """Wrap async generators with database connection and concurrency management.

    Ensures:
    1. Database connection is established once and reused
    2. Connection pool semaphore limits concurrent database operations
    3. Connection pool statistics are logged
    """

    async def wrapper(*args, **kwargs):
        global _db_connected  # noqa: PLW0603
        client = db
        if client is not None and hasattr(client, "connect") and hasattr(client, "disconnect"):
            # Only connect once, reuse the connection
            async with _db_lock:
                if not _db_connected:
                    await client.connect()
                    _db_connected = True
                    _log_connection_pool_stats()
            # For async generators, limit concurrency per yield
            async for item in func(*args, **kwargs):
                async with _db_semaphore:
                    _log_connection_pool_stats()
                    yield item
        else:
            async for item in func(*args, **kwargs):
                yield item

    return wrapper


def _log_connection_pool_stats():
    """Extract and log database connection pool statistics."""
    try:
        # Access the underlying asyncpg pool from Prisma's engine
        # Using type ignore for private attribute access
        engine = getattr(db, "_engine", None)  # type: ignore[attr-defined]
        if engine and hasattr(engine, "_pool"):
            pool = engine._pool
            if pool:
                # Try to get active connections count
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
