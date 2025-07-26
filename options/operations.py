from log import Log
from models import OptionContractSnapshot, OptionsContract
from prisma import Prisma
from prisma.models import Options, OptionSnapshot
from util import (
    expiration_date_to_datetime,
    format_snapshot,
    get_current_datetime,
    ns_to_datetime,
)

db = Prisma(auto_register=True)


# TODO: Upsert Bulk ?
# TODO: advantage of using ContextManager ?


class ContractNotActiveError(Exception):
    pass


# TODO: replace with INSERT
async def upsert_option_contract(database: Prisma, contract: OptionsContract) -> Options:
    expiration_dt = expiration_date_to_datetime(contract.expiration_date)

    return await Options.prisma().upsert(
        where={
            "ticker": contract.ticker,
        },
        data={
            "create": {
                "ticker": contract.ticker,
                "underlying_ticker": contract.underlying_ticker,
                "strike_price": contract.strike_price,
                "expiration_date": expiration_dt,
                "contract_type": "CALL" if contract.contract_type == "call" else "PUT",
            },
            "update": {
                "underlying_ticker": contract.underlying_ticker,
                "strike_price": contract.strike_price,
                "expiration_date": expiration_dt,
                "contract_type": "CALL" if contract.contract_type == "call" else "PUT",
            },
        },
    )


# TODO: replace with INSERT


async def upsert_option_snapshot(
    database: Prisma, contract_ticker: str, snapshot: OptionContractSnapshot
) -> OptionSnapshot:
    """Upsert an option snapshot into the database.
    Indexed by ticker and last_updated.
    Links to the parent option contract via ticker.
    """  # noqa: D205
    last_updated_raw = snapshot.day.last_updated if snapshot.day.last_updated else None
    last_updated_dt = ns_to_datetime(last_updated_raw) if last_updated_raw else None
    curr_datetime = get_current_datetime()

    try:
        if last_updated_dt is None:
            raise ContractNotActiveError("last_updated is required for upsert_option_snapshot")

        result = await database.optionsnapshot.upsert(
            where={
                "ticker_last_updated": {
                    "ticker": contract_ticker,
                    "last_updated": last_updated_dt,
                }
            },
            data={
                "create": {
                    "open_interest": snapshot.open_interest,
                    "volume": snapshot.day.volume if snapshot.day else None,
                    "implied_vol": snapshot.implied_volatility,
                    "last_price": snapshot.day.close if snapshot.day else None,
                    "last_updated": last_updated_dt,
                    "last_crawled": curr_datetime,
                    "day_open": snapshot.day.open if snapshot.day else None,
                    "day_close": snapshot.day.close if snapshot.day else None,
                    "day_change": snapshot.day.change_percent if snapshot.day else None,
                    "option": {"connect": {"ticker": contract_ticker}},
                },
                "update": {
                    "open_interest": snapshot.open_interest,
                    "volume": snapshot.day.volume if snapshot.day else None,
                    "implied_vol": snapshot.implied_volatility,
                    "last_price": snapshot.day.close if snapshot.day else None,
                    "last_updated": last_updated_dt,
                    "last_crawled": curr_datetime,
                    "day_open": snapshot.day.open if snapshot.day else None,
                    "day_close": snapshot.day.close if snapshot.day else None,
                    "day_change": snapshot.day.change_percent if snapshot.day else None,
                    "option": {"connect": {"ticker": contract_ticker}},
                },
            },
        )

        Log.info(
            f"{curr_datetime} Added snapshot for {contract_ticker}: OI={snapshot.open_interest}"
        )
        Log.info(format_snapshot(contract_ticker, snapshot))

        return result
    except ContractNotActiveError as e:
        Log.warn(
            f"{curr_datetime}"
            f"{contract_ticker} is not active, Skipping upserting option snapshot: {e}"
        )

    except Exception as e:
        Log.error(
            f"{curr_datetime} Error upserting option snapshot for "
            f"{contract_ticker} at {last_updated_dt}: {e}"
        )


async def process_option_contracts(database: Prisma, contract: OptionsContract) -> Options:
    return await upsert_option_contract(database, contract)


async def process_option_snapshot(
    database: Prisma, contract_ticker: str, snapshot: OptionContractSnapshot
) -> OptionSnapshot:
    return await upsert_option_snapshot(database, contract_ticker, snapshot)
