import asyncio
import json
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables BEFORE importing modules that use Prisma.
# Resolve the project root explicitly so systemd WorkingDirectory doesn't matter.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(dotenv_path=_PROJECT_ROOT / ".env")

# noinspection PyUnresolvedReference
from cli.targets import TARGETS  # noqa: E402
from lib.observability import Log  # noqa: E402
from options.ingestor import OptionIngestor, OptionSnapshotsIngestor  # noqa: E402
from options.models import OptionIngestParams  # noqa: E402
from options.retriever import OptionRetriever  # noqa: E402

retriever = OptionRetriever()
ingestor = OptionIngestor(option_retriever=retriever)
snapshots_ingestor = OptionSnapshotsIngestor(option_retriever=retriever)
# Add the project directory to the Python path
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "options"))


def ping(event, context):
    """Ping function to keep the Lambda warm."""
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Lambda is warm!"}),
    }


def ingest_options_handler(event, context):
    underlying_assets = [OptionIngestParams(asset[0], asset[1], asset[2]) for asset in TARGETS]

    try:
        asyncio.run(ingestor.ingest_options(underlying_assets=underlying_assets))
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Options ingestion completed successfully"}),
        }
    except Exception as e:
        Log.error(f"Error during options ingestion: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


# @traced_span_sync(name="ingest_option_snapshots", attributes={"module": "ingestor"})
def ingest_option_snapshots_handler(event, context):
    try:
        asyncio.run(snapshots_ingestor.ingest_option_snapshots())
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Option snapshots ingestion completed successfully"}),
        }
    except Exception as e:
        Log.error(f"Error during option snapshots ingestion: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


# TODO implement Migration to Athena
def migrate_expired_options_handler(event, context):
    try:
        raise NotImplementedError("Expired options migration is not implemented yet.")

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


if __name__ == "__main__":
    #     # Log.info("-----------Ingesting options...")
    #     # ingest_options_handler(None, None)
    Log.info("-----------Ingesting option snapshots...")
    ingest_option_snapshots_handler(None, None)
