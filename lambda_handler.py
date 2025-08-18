import asyncio
import json

from lib.log.log import Log
from options.decorator import traced_span_sync
from options.ingestor import OptionIngestor
from options.models import OptionIngestParams
from options.retriever import OptionRetriever

retriever = OptionRetriever()
ingestor = OptionIngestor(option_retriever=retriever)

# Add the project directory to the Python path
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "options"))


# Replace TARGETS with a list of OptionIngestParams instances
TARGETS = [
    OptionIngestParams("NBIS", None, (2025, 2025)),
    OptionIngestParams("SE", None, (2025, 2025)),
    OptionIngestParams("NET", None, (2025, 2025)),
    OptionIngestParams("MU", None, (2025, 2026)),
    OptionIngestParams("STX", None, (2025, 2026)),
    OptionIngestParams("AMD", None, (2025, 2025)),
    OptionIngestParams("CRWV", None, (2025, 2025)),
    OptionIngestParams("META", None, (2025, 2025)),
    OptionIngestParams("MP", None, (2025, 2025)),
    OptionIngestParams("SNOW", None, (2025, 2025)),
    OptionIngestParams("HOOD", (100, 150), (2025, 2025)),
    # # ---
    # OptionIngestParams("FCX", (30, 50), (2025, 2025)),
]


def ping(event, context):
    """Ping function to keep the Lambda warm."""
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Lambda is warm!"}),
    }


def ingest_options_handler(event, context):
    try:
        asyncio.run(ingestor.ingest_options(TARGETS))
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Options ingestion completed successfully"}),
        }
    except Exception as e:
        Log.error(f"Error during options ingestion: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


@traced_span_sync(name="ingest_option_snapshots", attributes={"module": "ingestor"})
def ingest_option_snapshots_handler(event, context):
    try:
        asyncio.run(ingestor.ingest_option_snapshots())
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
    Log.info("-----------Ingesting options...")
    ingest_options_handler(None, None)
    Log.info("-----------Ingesting option snapshots...")
    ingest_option_snapshots_handler(None, None)
