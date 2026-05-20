# Skip running this integration-only module during unit tests
# pytest.skip("integration-only script; skip during unit tests", allow_module_level=True)

import asyncio
import logging

from microservices.option_ingestor.api import Fetcher
from microservices.shared.decorator import traced_span_async

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@traced_span_async(name="test_polygon", attributes={"testcase": "decorator"})
def test_fetch():
    core = Fetcher("AAPL")

    core.get_call_contracts()


# @traced_span_async(name="mock_db_upsert", attributes={"testcase": "db"})
# async def mock_db_upsert(snapshot):

#     await asyncio.sleep(1)  # Simulate DB latency
#     await asyncio.sleep(1)  # Simulate DB latency


@traced_span_async(name="test_polygon", attributes={"testcase": "decorator"})
async def test_fetch_async():
    core = Fetcher("AAPL")
    snapshot = await core.fetch_daily_snapshot_async("NBIS", "O:NBIS251121C00070000")
    logger.info("Fetched snapshot: %s", snapshot)
    # await mock_db_upsert(snapshot)


if __name__ == "__main__":
    import asyncio

    async def main():
        tasks = [test_fetch_async() for _ in range(50)]
        errors = 0
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, result in enumerate(results, 1):
            if isinstance(result, Exception):
                errors += 1
                logger.error("Run %s: Error - %s", i, result)
        logger.info("Total errors: %s", errors)

    asyncio.run(main())
