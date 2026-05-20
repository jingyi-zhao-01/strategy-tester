import os
from datetime import datetime

import pytz
from dotenv import load_dotenv
from polygon import RESTClient

from microservices.shared.models import OptionContractSnapshot
from microservices.shared.models.option_models import OptionSymbol

if not os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
    load_dotenv()

DEFAULT_TIME_ZONE = "America/New_York"
TIME_ZONE = os.getenv("INGEST_TIME_ZONE", DEFAULT_TIME_ZONE)


def ns_to_datetime(ns: int) -> datetime:
    nyc_tz = pytz.timezone(TIME_ZONE)
    utc_dt = datetime.fromtimestamp(ns / 1e9, tz=pytz.UTC)
    return utc_dt.astimezone(nyc_tz)


def option_expiration_date_to_datetime(expiration_date: str) -> datetime:
    year, month, day = map(int, expiration_date.split("-"))
    nyc_tz = pytz.timezone(TIME_ZONE)
    return nyc_tz.localize(datetime(year, month, day, 23, 59, 0))


def get_current_datetime(granularity: str = "second") -> datetime:
    nyc_tz = pytz.timezone(TIME_ZONE)
    now = datetime.now(nyc_tz)

    if granularity == "year":
        return now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    if granularity == "month":
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if granularity == "day":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if granularity == "hour":
        return now.replace(minute=0, second=0, microsecond=0)
    if granularity == "minute":
        return now.replace(second=0, microsecond=0)
    if granularity == "second":
        return now
    raise ValueError(
        "Invalid granularity. Choose from 'year', 'month', 'day', 'hour', 'minute', 'second'."
    )


def convert_to_nyc_time(timestamp_ms):
    nyc_tz = pytz.timezone(TIME_ZONE)
    utc_dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=pytz.utc)
    nyc_dt = utc_dt.astimezone(nyc_tz)
    return nyc_dt.strftime("%y-%m-%d-%H")


def convert_to_nyc_time_ns(timestamp_ns):
    nyc_tz = pytz.timezone(TIME_ZONE)
    utc_dt = datetime.fromtimestamp(timestamp_ns / 1_000_000_000, tz=pytz.utc)
    nyc_dt = utc_dt.astimezone(nyc_tz)
    return nyc_dt.strftime("%y-%m-%d-%H-%M")


def get_polygon_client():
    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        raise ValueError(
            "POLYGON_API_KEY not found in environment variables. Please check your .env file."
        )
    return RESTClient(api_key)


def parse_option_symbol(symbol: str, underlying_asset: str) -> OptionSymbol:
    clean_symbol = symbol.replace("O:", "")
    date_start_idx = len(underlying_asset)

    underlying = clean_symbol[:date_start_idx]
    date_part = clean_symbol[date_start_idx : date_start_idx + 6]

    if underlying != underlying_asset:
        raise ValueError(
            f"Symbol underlying '{underlying}' doesn't match expected '{underlying_asset}'"
        )

    year = int("20" + date_part[:2])
    month = int(date_part[2:4])
    day = int(date_part[4:6])

    contract_type = "CALL" if clean_symbol[date_start_idx + 6] == "C" else "PUT"
    strike = float(clean_symbol[date_start_idx + 7 :]) / 1000

    return OptionSymbol(
        underlying=underlying,
        expiration=datetime(year, month, day),
        contract_type=contract_type,
        strike=strike,
    )


def format_snapshot(contract_ticker: str, snapshot: OptionContractSnapshot) -> str:
    iv = f"{snapshot.implied_volatility:.2%}" if snapshot.implied_volatility is not None else "N/A"
    day_volume = (
        snapshot.day.volume
        if snapshot.day is not None and snapshot.day.volume is not None
        else "N/A"
    )
    last_updated = _day_attr(snapshot, "last_updated")
    day_open = _fmt_currency(_day_attr(snapshot, "open"))
    day_close = _fmt_currency(_day_attr(snapshot, "close"))
    day_change = _fmt_percent(_day_attr(snapshot, "change_percent"))
    greeks_str = _format_greeks(snapshot)
    return (
        f"Ticker: {contract_ticker} | "
        f"OI: {snapshot.open_interest if snapshot.open_interest is not None else 'N/A'} | "
        f"Day Volume: {day_volume} | "
        f"IV: {iv} | "
        f"Greeks: {greeks_str} | "
        f"DayOpen: {day_open} | "
        f"DayClose: {day_close} | "
        f"Day Price Change: {day_change} | "
        f"Last Updated: {last_updated if last_updated is not None else 'N/A'}"
    )


def _day_attr(snapshot: OptionContractSnapshot, attr: str):
    if snapshot.day is None:
        return None
    return getattr(snapshot.day, attr, None)


def _fmt_currency(value) -> str:
    return f"${value:.2f}" if value is not None else "N/A"


def _fmt_percent(value) -> str:
    return f"{value:.2f}%" if value is not None else "N/A"


def _format_greeks(snapshot: OptionContractSnapshot) -> str:
    if snapshot.greeks is None:
        return "N/A"

    greek_specs = [
        ("delta", "Δ"),
        ("gamma", "Γ"),
        ("theta", "Θ"),
        ("vega", "ν"),
    ]
    parts = []
    for attr, symbol in greek_specs:
        value = getattr(snapshot.greeks, attr, None)
        if value is not None:
            parts.append(f"{symbol}:{value:.4f}")

    return " ".join(parts) if parts else "N/A"
