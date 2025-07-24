from collections import defaultdict
from util import convert_to_nyc_time, get_polygon_client

client = get_polygon_client()

# target_option_ticker = ["O:MP270115C00055000", "O:MP270815C00041000"]

target_ticker = ["O:MP270115C00055000", "O:MP250815C00041000"]

pheripheral_ticker = ["O:MP260515C00050000"]


total_tickers = target_ticker + pheripheral_ticker


aggs_map = defaultdict(list)

for ticker in total_tickers:
    for a in client.list_aggs(
        ticker,
        1,
        "hour",
        "2025-06-01",
        "2025-07-09",
        adjusted="false",
        sort="asc",
        limit=120,
    ):
        aggs_map[ticker].append(a)

for ticker, aggs in aggs_map.items():
    print("--------------------------------------")
    for agg in aggs:
        # If agg is an object, convert to dict
        agg_dict = agg.__dict__ if hasattr(agg, "__dict__") else agg
        volume = agg_dict.get("volume")
        time = convert_to_nyc_time(agg_dict.get("timestamp"))
        vwap = agg_dict.get("vwap")
        open = agg_dict.get("open")
        close = agg_dict.get("close")
        transactions = agg_dict.get("transactions")
        print(
            f"Ticker: {ticker}, Volume: {volume}, Date: {time}, Transactions: {transactions}, VWAP: {vwap}, Open: {open}, Close: {close}"
        )
