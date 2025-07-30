import asyncio
import json

from lib.log.log import Log
from options import ingestor
from options.models import OptionIngestParams

# Add the project directory to the Python path
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "options"))


# Replace TARGETS with a list of OptionIngestParams instances
TARGETS = [
    OptionIngestParams("NBIS", (40, 70), (2025, 2025)),
    OptionIngestParams("SE", (140, 200), (2025, 2025)),
    OptionIngestParams("HOOD", (100, 150), (2025, 2025)),
    OptionIngestParams("NET", (185, 210), (2025, 2025)),
    OptionIngestParams("MU", (90, 150), (2025, 2026)),
    OptionIngestParams("CRWV", (100, 120), (2025, 2025)),
    OptionIngestParams("STX", (100, 200), (2025, 2026)),
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
