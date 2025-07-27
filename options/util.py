import os
from datetime import datetime

import pytz
from dotenv import load_dotenv
from polygon import RESTClient

from options.models import OptionContractSnapshot
from options.models.option_models import OptionSymbol

# Load environment variables from .env file
load_dotenv()

TIME_ZONE = "America/New_York"


def ns_to_datetime(
    ns: int,
) -> datetime:
    nyc_tz = pytz.timezone(TIME_ZONE)
    # First convert to UTC
    utc_dt = datetime.fromtimestamp(ns / 1e9, tz=pytz.UTC)
    # Then convert to NYC timezone
    return utc_dt.astimezone(nyc_tz)


def expiration_date_to_datetime(expiration_date: str) -> datetime:
    year, month, day = map(int, expiration_date.split("-"))
    return datetime(year, month, day, tzinfo=pytz.timezone(TIME_ZONE))


def get_current_datetime(granularity: str = "second") -> datetime:
    """Get the current datetime in NYC timezone with specified granularity.

    Args:
    ----
        granularity (str, optional): Time granularity.
            Options: "year", "month", "day", "hour", "minute", "second".
            Defaults to "second".

    Returns:
    -------
        datetime: Current datetime in NYC timezone with specified granularity

    """
    nyc_tz = pytz.timezone(TIME_ZONE)
    now = datetime.now(nyc_tz)

    if granularity == "year":
        return now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    elif granularity == "month":
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif granularity == "day":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif granularity == "hour":
        return now.replace(minute=0, second=0, microsecond=0)
    elif granularity == "minute":
        return now.replace(second=0, microsecond=0)
    elif granularity == "second":
        return now
    else:
        raise ValueError(
            "Invalid granularity. Choose from 'year', 'month', 'day', 'hour', 'minute', 'second'."
        )


def convert_to_nyc_time(timestamp_ms):
    nyc_tz = pytz.timezone("America/New_York")
    # Step 1 & 2: Convert ms to seconds and create UTC datetime
    utc_dt = datetime.utcfromtimestamp(timestamp_ms / 1000).replace(tzinfo=pytz.utc)
    # Step 3: Convert to NYC timezone
    nyc_dt = utc_dt.astimezone(nyc_tz)
    # Step 4: Format as YY-MM-DD-HH-MM-SS
    # return nyc_dt.strftime("%y-%m-%d-%H-%M-%S")
    return nyc_dt.strftime("%y-%m-%d-%H")


def convert_to_nyc_time_ns(timestamp_ns):
    nyc_tz = pytz.timezone("America/New_York")
    utc_dt = datetime.utcfromtimestamp(timestamp_ns / 1_000_000_000).replace(tzinfo=pytz.utc)
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
    # Remove option prefix if present
    clean_symbol = symbol.replace("O:", "")
    date_start_idx = len(underlying_asset)

    underlying = clean_symbol[:date_start_idx]
    date_part = clean_symbol[date_start_idx : date_start_idx + 6]

    if underlying != underlying_asset:
        raise ValueError(
            f"Symbol underlying '{underlying}' doesn't match expected '{underlying_asset}'"
        )

    year = int("20" + date_part[:2])  # 2027
    month = int(date_part[2:4])  # 01
    day = int(date_part[4:6])  # 15

    contract_type = "CALL" if clean_symbol[date_start_idx + 6] == "C" else "PUT"
    strike = float(clean_symbol[date_start_idx + 7 :]) / 1000  # 250.00

    return OptionSymbol(
        underlying=underlying,
        expiration=datetime(year, month, day),
        contract_type=contract_type,
        strike=strike,
    )


def format_snapshot(contract_ticker: str, snapshot: OptionContractSnapshot) -> str:
    iv = f"{snapshot.implied_volatility:.2%}" if snapshot.implied_volatility else "N/A"
    day_open = f"${snapshot.day.open:.2f}" if snapshot.day.open else "N/A"
    day_close = f"${snapshot.day.close:.2f}" if snapshot.day.close else "N/A"
    day_change = f"{snapshot.day.change_percent:.2f}%" if snapshot.day.change_percent else "N/A"
    return (
        f"Ticker: {contract_ticker} | "
        f"OI: {snapshot.open_interest or 'N/A'} | "
        f"Day Volume: {snapshot.day.volume or 'N/A'} | "
        f"IV: {iv} | "
        # f"Greeks: {snapshot.greeks or 'N/A'} | "
        f"DayOpen: {day_open} | "
        f"DayClose: {day_close} | "
        f"Day Price Change: {day_change} | "
        f"Last Updated: {snapshot.day.last_updated or 'N/A'}"
    )
