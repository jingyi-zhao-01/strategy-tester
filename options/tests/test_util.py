from datetime import datetime
from unittest import mock

import pytest
import pytz

from options.util import (
    TIME_ZONE,
    OptionContractSnapshot,
    convert_to_nyc_time,
    convert_to_nyc_time_ns,
    format_snapshot,
    get_current_datetime,
    get_polygon_client,
    ns_to_datetime,
    option_expiration_date_to_datetime,
    parse_option_symbol,
)

TEST_YEAR = 2025
TEST_MONTH = 7
TEST_DAY = 31
NS_TO_DATETIME = 1753953600000000000
MS_TO_NYC_TIME = 1753953600000
NS_TO_NYC_TIME = 1753953600000000000
EXPECTED_SPLIT_4 = 4
EXPECTED_SPLIT_5 = 5
EXPECTED_STRIKE = 250.0
EXPECTED_EXP_YEAR = 2024
EXPECTED_EXP_MONTH = 2
EXPECTED_EXP_DAY = 15


def test_ns_to_datetime():
    dt = ns_to_datetime(NS_TO_DATETIME)
    assert dt.year == TEST_YEAR and dt.month == TEST_MONTH and dt.day == TEST_DAY
    assert dt.tzinfo.zone == "America/New_York"


def test_get_current_datetime_granularity():
    dt = get_current_datetime("year")
    assert dt.month == 1 and dt.day == 1 and dt.hour == 0
    dt = get_current_datetime("month")
    assert dt.day == 1 and dt.hour == 0
    dt = get_current_datetime("day")
    assert dt.hour == 0
    dt = get_current_datetime("hour")
    assert dt.minute == 0
    dt = get_current_datetime("minute")
    assert dt.second == 0
    dt = get_current_datetime("second")
    assert isinstance(dt, datetime)
    with pytest.raises(ValueError):
        get_current_datetime("invalid")


def test_convert_to_nyc_time():
    result = convert_to_nyc_time(MS_TO_NYC_TIME)
    assert isinstance(result, str)
    assert len(result.split("-")) == EXPECTED_SPLIT_4


def test_convert_to_nyc_time_ns():
    result = convert_to_nyc_time_ns(NS_TO_NYC_TIME)
    assert isinstance(result, str)
    assert len(result.split("-")) == EXPECTED_SPLIT_5


def test_get_polygon_client(monkeypatch):
    monkeypatch.setenv("POLYGON_API_KEY", "dummy")
    client = get_polygon_client()
    assert client is not None
    monkeypatch.delenv("POLYGON_API_KEY", raising=False)
    with pytest.raises(ValueError):
        get_polygon_client()


def test_parse_option_symbol():
    symbol = "AAPL240215C00250000"
    parsed = parse_option_symbol(symbol, "AAPL")
    assert parsed.underlying == "AAPL"
    assert parsed.contract_type == "CALL"
    assert parsed.strike == EXPECTED_STRIKE
    assert parsed.expiration.year == EXPECTED_EXP_YEAR
    assert parsed.expiration.month == EXPECTED_EXP_MONTH
    assert parsed.expiration.day == EXPECTED_EXP_DAY
    with pytest.raises(ValueError):
        parse_option_symbol("WRONG240215C00250000", "AAPL")


def test_format_snapshot():
    snapshot = OptionContractSnapshot(
        implied_volatility=0.25,
        open_interest=100,
        day=mock.Mock(
            open=1.23,
            close=1.45,
            change_percent=0.05,
            volume=200,
            last_updated="2025-07-31T12:00:00Z",
        ),
    )
    result = format_snapshot("AAPL240215C00250000", snapshot)
    assert "Ticker: AAPL240215C00250000" in result
    assert "OI: 100" in result
    assert "IV: 25.00%" in result


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
