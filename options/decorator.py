import asyncio
import contextlib

from dotenv import load_dotenv
from opentelemetry import trace
from opentelemetry.trace import SpanKind

from prisma import Prisma

load_dotenv()


# TODO: Open Interest vs expiration date vs strike price

CONCURRENCY_LIMIT = 200
DATA_BASE_CONCURRENCY_LIMIT = 700
OPTION_BATCH_RETRIEVAL_SIZE = 500


# Initialize OpenTelemetry providers
# resource = Resource.create({"service.name": "polygon"})
# tp = TracerProvider(resource=resource)
# tp.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
# trace.set_tracer_provider(tp)


# SystemMetricsInstrumentor().instrument()
# tracer = trace.get_tracer("polygon")
tracer = trace.get_tracer(__name__)

semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
# TODO: Lazy DB client; will be provided via monkeypatch in tests or resolved at runtime.
# Avoid importing/initializing Prisma at import time to prevent errors when the client
# hasn't been generated or when DB is unavailable.
db = Prisma(auto_register=True)


def bounded_db_connection(func):
    async def wrapper(*args, **kwargs):
        client = db
        if client is not None and hasattr(client, "connect") and hasattr(client, "disconnect"):
            await client.connect()
            try:
                return await func(*args, **kwargs)
            finally:
                await client.disconnect()
        else:
            return await func(*args, **kwargs)

    return wrapper


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
