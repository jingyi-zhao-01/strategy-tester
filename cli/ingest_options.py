"""Script to ingest option contracts from Polygon API."""

from microservices.option_ingestor.service import run


def main():
    """Ingest option contracts from Polygon API into the database."""
    run()


if __name__ == "__main__":
    main()
