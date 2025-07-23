import asyncio
from client import get_db
from prisma.models import OptionSnapshot


async def test_db_connection():
    """Test database connection and basic operations"""
    try:
        print("Testing database connection...")
        async with get_db() as db:
            # Test connection by attempting a simple query
            count = await db.optionsnapshot.count()
            print(f"✅ Successfully connected to database")
            print(f"Found {count} option snapshots in database")

            # Get table info
            print("\nDatabase schema verification:")
            tables = await db.query_raw(
                "SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname='public'"
            )
            print(f"Available tables: {[table['tablename'] for table in tables]}")

            # Check if our table exists
            if any(table["tablename"] == "option_snapshots" for table in tables):
                print("✅ option_snapshots table exists")
            else:
                print("❌ option_snapshots table not found")

        return True
    except Exception as e:
        print(f"❌ Connection test failed: {str(e)}")
        return False


if __name__ == "__main__":
    print("Running database connection test...")
    asyncio.run(test_db_connection())
