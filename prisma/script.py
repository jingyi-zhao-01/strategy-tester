import asyncio

# import json
from prisma import Prisma


async def main() -> None:
    db = Prisma(auto_register=True)
    await db.connect()

    # sample_data = {
    #     "preferences": {"theme": "dark", "notifications": True},
    #     "history": [
    #         {"action": "login", "timestamp": "2025-08-03T12:00:00Z"},
    #         {"action": "logout", "timestamp": "2025-08-03T14:00:00Z"},
    #     ],
    # }

    # user = await db.users.upsert(
    #     where={"email": "robert@craigie.dev"},
    #     data={
    #         "create": {
    #             "name": "Robert",
    #             "email": "robert@craigie.dev",
    #             "data": json.dumps(sample_data),
    #         },
    #         "update": {
    #             "name": "Robert",
    #             "email": "robert@craigie.dev",
    #             "data": json.dumps(sample_data),
    #         },
    #     },
    # )

    await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
