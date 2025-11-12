import json
import logging
import sys

from dotenv import dotenv_values


def convert_dotenv_to_sam_json(dotenv_path, json_path):
    """Convert a .env file to a SAM-compatible JSON environment file."""
    config = dotenv_values(dotenv_path)

    # Filter out comments or empty lines if any are picked up
    sam_params = {key: value for key, value in config.items() if value is not None}

    sam_config = {"Parameters": sam_params}

    with open(json_path, "w") as f:
        json.dump(sam_config, f, indent=2)


if __name__ == "__main__":
    EXPECTED_ARG_COUNT = 3
    if len(sys.argv) != EXPECTED_ARG_COUNT:
        logging.error(
            "Usage: python prepare-sam-env.py <path/to/.env.file> <path/to/output.json.file>"
        )
        sys.exit(1)

    dotenv_file = sys.argv[1]
    json_file = sys.argv[2]

    convert_dotenv_to_sam_json(dotenv_file, json_file)
    logging.info(f"Successfully converted {dotenv_file} to {json_file}")
