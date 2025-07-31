from datetime import datetime

import pytest
import pytz

from options.util import TIME_ZONE, option_expiration_date_to_datetime


def test_option_expiration_date_to_datetime_basic():
    dt = option_expiration_date_to_datetime("2025-12-19")
    nyc_tz = pytz.timezone(TIME_ZONE)
    expected = nyc_tz.localize(datetime(2025, 12, 19, 23, 59, 0))
    assert dt == expected
    assert dt.tzinfo.zone == nyc_tz.zone


@pytest.mark.parametrize(
    "date_str,expected_tuple",
    [
        ("2024-01-01", (2024, 1, 1, 23, 59, 0)),
        ("2023-07-31", (2023, 7, 31, 23, 59, 0)),
        ("2030-02-28", (2030, 2, 28, 23, 59, 0)),
    ],
)
def test_option_expiration_date_to_datetime_various(date_str, expected_tuple):
    dt = option_expiration_date_to_datetime(date_str)
    nyc_tz = pytz.timezone(TIME_ZONE)
    expected = nyc_tz.localize(datetime(*expected_tuple))
    assert dt == expected


def test_option_expiration_date_to_datetime_invalid():
    with pytest.raises(ValueError):
        option_expiration_date_to_datetime("not-a-date")
