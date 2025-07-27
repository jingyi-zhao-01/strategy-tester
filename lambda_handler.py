import asyncio
import json

from options.ingestor import ingest_option_snapshots, ingest_options

# Add the project directory to the Python path
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "options"))

# Import the main function from options/main.py


# def lambda_handler(event, context):
#     try:
#         # # Run the setup and main async functions
#         # asyncio.run(main())
#         return {
#             "statusCode": 200,
#             "body": json.dumps({"message": "Options processing completed successfully"}),
#         }
#     except Exception as e:
#         return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


UNDERLYING_ASSET = "NBIS"
PRICE_RANGE = (40, 70)
YEAR_RANGE = (2025, 2025)


def ping(event, context):
    """Ping function to keep the Lambda warm."""
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Lambda is warm!"}),
    }


def ingest_options_handler(event, context):
    try:
        asyncio.run(
            ingest_options(
                underlying_asset=UNDERLYING_ASSET,
                price_range=PRICE_RANGE,
                year_range=YEAR_RANGE,
            )
        )
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Options ingestion completed successfully"}),
        }
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


def ingest_option_snapshots_handler(event, context):
    try:
        asyncio.run(
            ingest_option_snapshots(
                underlying_asset=UNDERLYING_ASSET,
                price_range=PRICE_RANGE,
                year_range=YEAR_RANGE,
            )
        )
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Option snapshots ingestion completed successfully"}),
        }
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


if __name__ == "__main__":
    # ingest_options_handler(None, None)
    ingest_option_snapshots_handler(None, None)
