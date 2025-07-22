import pytz
from datetime import datetime

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