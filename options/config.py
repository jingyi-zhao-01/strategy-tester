import asyncio

from prisma import Prisma

db = Prisma(auto_register=True)
# TODO: Open Interest vs expiration date vs strike price

CONCURRENCY_LIMIT = 200
OPTION_BATCH_RETRIEVAL_SIZE = 500
semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)


# TODO: Benchmark on Semaphore


def bounded_db_connection(func):
    async def wrapper(*args, **kwargs):
        await db.connect()
        try:
            return await func(*args, **kwargs)
        finally:
            await db.disconnect()

    return wrapper


def bounded_async_sem(limit=CONCURRENCY_LIMIT):
    def wrapper(coro):
        async def inner(*args, **kwargs):
            sem = asyncio.Semaphore(limit) if limit else semaphore
            async with sem:
                return await coro(*args, **kwargs)

        return inner

    return wrapper
