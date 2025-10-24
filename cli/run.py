import os
import subprocess
import sys

from dotenv import load_dotenv


def main():
    # Load environment variables from .env
    load_dotenv()

    # Prepare environment for subprocess
    env = os.environ.copy()

    # Build the command to run lambda_handler.py with opentelemetry-instrument
    cmd = [
        "opentelemetry-instrument",
        sys.executable,
        os.path.join(os.path.dirname(__file__), "lambda_handler.py"),
    ]

    # Run the command with the loaded environment
    subprocess.run(cmd, env=env, check=False)


if __name__ == "__main__":
    main()
