import asyncio

from lib.log.log import Log
from prisma import Prisma
from prisma.models import User


async def main() -> None:
    db = Prisma(auto_register=True)
    await db.connect()

    user = await User.prisma().upsert(
        where={"email": "robert@craigie.dev"},
        data={
            "create": {"name": "Robert", "email": "robert@craigie.dev"},
            "update": {"name": "Robert", "email": "robert@craigie.dev"},
        },
    )

    await db.disconnect()
    Log(f"User created: {user.name} with email {user.email}")


if __name__ == "__main__":
    asyncio.run(main())
