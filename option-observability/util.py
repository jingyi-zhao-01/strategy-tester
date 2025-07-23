import pytz
import os
from datetime import datetime
from polygon import RESTClient
from dotenv import load_dotenv
from models.option_models import OptionSymbolComponents

# Load environment variables from .env file
load_dotenv()


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
    utc_dt = datetime.utcfromtimestamp(timestamp_ns / 1_000_000_000).replace(
        tzinfo=pytz.utc
    )
    nyc_dt = utc_dt.astimezone(nyc_tz)
    return nyc_dt.strftime("%y-%m-%d-%H-%M")


def get_polygon_client():

    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        raise ValueError(
            "POLYGON_API_KEY not found in environment variables. Please check your .env file."
        )
    return RESTClient(api_key)


def parse_option_symbol(symbol: str, underlying_asset: str) -> OptionSymbolComponents:

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

    return OptionSymbolComponents(
        underlying=underlying,
        expiration=datetime(year, month, day),
        contract_type=contract_type,
        strike=strike,
    )
