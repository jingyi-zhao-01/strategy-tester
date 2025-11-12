import json

from cli.ingest_options import main as ingest_options_main
from cli.ingest_snapshots import main as ingest_snapshots_main
from lib.observability import Log


def ping(event, context):
    """Ping function to keep the Lambda warm."""
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Lambda is warm!"}),
    }


def ingest_options_handler(event, context):
    """Lambda handler to trigger the ingestion of option contracts."""
    try:
        ingest_options_main()
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Options ingestion completed successfully"}),
        }
    except Exception as e:
        Log.error(f"Error during options ingestion: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


def ingest_option_snapshots_handler(event, context):
    """Lambda handler to trigger the ingestion of option snapshots."""
    try:
        ingest_snapshots_main()
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Option snapshots ingestion completed successfully"}),
        }
    except Exception as e:
        Log.error(f"Error during option snapshots ingestion: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


def migrate_expired_options_handler(event, context):
    """Lambda handler for migrating expired options. Not yet implemented."""
    try:
        raise NotImplementedError("Expired options migration is not implemented yet.")
    except Exception as e:
        Log.error(f"Error during expired options migration: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
