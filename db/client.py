from prisma import Prisma
from contextlib import asynccontextmanager
from typing import AsyncGenerator


@asynccontextmanager
async def get_db() -> AsyncGenerator[Prisma, None]:
    """
    Context manager for database connections.
    Usage:
        async with get_db() as db:
            result = await db.optionsnapshot.find_many()
    """
    db = Prisma()
    await db.connect()
    try:
        yield db
    finally:
        await db.disconnect()



