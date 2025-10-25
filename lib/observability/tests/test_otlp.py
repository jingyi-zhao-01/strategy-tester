#!/usr/bin/env python3
"""Test script to verify OTLP logging is working."""

import time

from lib.observability import Log


def main():
    """Test OTLP logging."""
    Log.info("Testing OTLP logging...")

    # Log some test messages
    Log.info("Test info message from OTLP test")
    Log.warn("Test warning message from OTLP test")
    Log.error("Test error message from OTLP test")

    Log.info("Logs sent. Waiting 10 seconds for batch export...")
    time.sleep(10)  # Wait for batch export

    Log.info("Test completed. Check your OTLP endpoint for the logs.")


if __name__ == "__main__":
    main()
