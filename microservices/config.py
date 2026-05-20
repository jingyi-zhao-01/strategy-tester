"""Environment-driven configuration for ingestion microservices."""

import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from cli.targets import TARGETS
from microservices.shared.models import OptionIngestParams


@dataclass(frozen=True)
class RuntimeConfig:
    """Runtime behavior shared by all ingestion services."""

    service_name: str
    enable_otel: bool


@dataclass(frozen=True)
class RetrieverConfig:
    """Retriever-level runtime configuration."""

    concurrency_limit: int
    batch_size: int


def load_env() -> None:
    """Load dotenv file into process environment when explicitly configured."""
    dotenv_path = os.getenv("DOTENV_PATH")
    if dotenv_path:
        load_dotenv(dotenv_path=Path(dotenv_path), override=False)


def parse_bool(env_key: str, default: bool) -> bool:
    value = os.getenv(env_key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def parse_int(env_key: str, default: int) -> int:
    value = os.getenv(env_key)
    if value is None or value.strip() == "":
        return default
    return int(value)


def get_retriever_config() -> RetrieverConfig:
    """Build retriever configuration from environment variables."""
    return RetrieverConfig(
        concurrency_limit=parse_int("INGEST_CONCURRENCY_LIMIT", 200),
        batch_size=parse_int("INGEST_OPTION_BATCH_SIZE", 500),
    )


def get_option_runtime_config() -> RuntimeConfig:
    """Build Option Ingestor runtime configuration from environment variables."""
    return RuntimeConfig(
        service_name=os.getenv("OPTION_INGEST_SERVICE_NAME", "option-ingestor"),
        enable_otel=parse_bool("OPTION_INGEST_ENABLE_OTEL", True),
    )


def get_snapshot_runtime_config() -> RuntimeConfig:
    """Build Snapshot Ingestor runtime configuration from environment variables."""
    return RuntimeConfig(
        service_name=os.getenv("SNAPSHOT_INGEST_SERVICE_NAME", "snapshot-ingestor"),
        enable_otel=parse_bool("SNAPSHOT_INGEST_ENABLE_OTEL", True),
    )


def _option_param_from_dict(payload: dict) -> OptionIngestParams:
    symbol = payload["symbol"]
    price_range = payload.get("price_range")
    year_start = parse_int("OPTION_INGEST_DEFAULT_YEAR_START", 2026)
    year_end = parse_int("OPTION_INGEST_DEFAULT_YEAR_END", year_start)
    year_range = payload.get("year_range", [year_start, year_end])
    return OptionIngestParams(
        symbol, tuple(price_range) if price_range else None, tuple(year_range)
    )


def get_option_targets_from_env() -> list[OptionIngestParams]:
    """Parse option ingest targets from env.

    Supported formats:
    - OPTION_INGEST_TARGETS: JSON array of strings or objects
      Example: '["NVDA", {"symbol":"AAPL","price_range":[100,250],"year_range":[2026,2027]}]'
    - OPTION_INGEST_SYMBOLS: comma-separated symbols with shared year range defaults
    """
    raw_targets = os.getenv("OPTION_INGEST_TARGETS", "").strip()
    if raw_targets:
        parsed = json.loads(raw_targets)
        targets: list[OptionIngestParams] = []
        for item in parsed:
            if isinstance(item, str):
                year_start = parse_int("OPTION_INGEST_DEFAULT_YEAR_START", 2026)
                year_end = parse_int("OPTION_INGEST_DEFAULT_YEAR_END", year_start)
                targets.append(OptionIngestParams(item, None, (year_start, year_end)))
            elif isinstance(item, dict):
                targets.append(_option_param_from_dict(item))
            else:
                raise ValueError("OPTION_INGEST_TARGETS entries must be string or object")
        return targets

    raw_symbols = os.getenv("OPTION_INGEST_SYMBOLS", "").strip()
    if raw_symbols:
        year_start = parse_int("OPTION_INGEST_DEFAULT_YEAR_START", 2026)
        year_end = parse_int("OPTION_INGEST_DEFAULT_YEAR_END", year_start)
        symbols = [symbol.strip() for symbol in raw_symbols.split(",") if symbol.strip()]
        return [OptionIngestParams(symbol, None, (year_start, year_end)) for symbol in symbols]

    return [
        OptionIngestParams(asset, price_range, year_range)
        for asset, price_range, year_range in TARGETS
    ]
