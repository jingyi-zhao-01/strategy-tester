from polygon import RESTClient

client = RESTClient("1TxWblBP3vePJcP2O84xMNFxvp25tYA7")
ASSET = "SE"

contracts = []
for c in client.list_options_contracts(
	underlying_ticker=ASSET,
	contract_type="call",
	# strike_price=55,
	expired="false",
	order="desc",
	limit=20,
	sort="strike_price",
	):
    contracts.append(c)

for c in contracts:
    print(
        c.ticker,
        c.strike_price,
        c.expiration_date,
        c.contract_type
    )