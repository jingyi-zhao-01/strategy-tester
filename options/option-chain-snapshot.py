from util import convert_to_nyc_time_ns, get_polygon_client

client = get_polygon_client()

option_chains = []

# params = [55, "2025-08-15", "call"]
ASSET = "SE"
# params = [55, "2027-01-15", "put"]
params = [165, "2025-08-08", "call"]



# Option chain snapshot day

for o in client.list_snapshot_options_chain(
    ASSET,
    params={
        "strike_price": params[0],
        "expiration_date": params[1],
        "order": "asc",
        "limit": 10,
        "sort": "ticker",
        "contract_type": params[2],
    },
):
    option_chains.append(o)

for option_chain in option_chains:
    x = option_chain
    print(f"open_interest: {option_chain.open_interest}, "
          f"implied_volatility: {option_chain.implied_volatility}, "
          f"greeks: {option_chain.greeks}, "
        f"day.change_percent: {option_chain.day.change_percent}, "
        f"day.last_updated: {convert_to_nyc_time_ns(option_chain.day.last_updated)}, "
          f"day.volume: {option_chain.day.volume}, "
          f"day.close: {option_chain.day.close}, "
    )

