from lib import Log
from options.util import (
    expiration_date_to_datetime,
    format_snapshot,
    get_current_datetime,
    ns_to_datetime,
)
from prisma import Prisma
from prisma.errors import UniqueViolationError
from prisma.models import Options, OptionSnapshot

from .models import OptionContractSnapshot, OptionsContract

db = Prisma(auto_register=True)


# TODO: Upsert Bulk ?
# TODO: advantage of using ContextManager ?


class ContractNotActiveError(Exception):
    pass


async def get_all_option_contracts(database: Prisma) -> list[Options]:
    """Fetch all option contracts from the database."""
    try:
        contracts = await Options.prisma().find_many()
        Log.info(f"Retrieved {len(contracts)} option contracts from the database.")
        return contracts
    except Exception as e:
        Log.error(f"Error fetching option contracts: {e}")
        return []


# TODO: replace with INSERT
async def upsert_option_contract(database: Prisma, contract: OptionsContract) -> Options:
    expiration_dt = expiration_date_to_datetime(contract.expiration_date)

    Log.info(
        f"Upserting contract: {contract.ticker}, "
        f"Strike: {contract.strike_price}, "
        f"Expiration: {expiration_dt}, "
        f"Type: {contract.contract_type}"
    )

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


async def insert_option_snapshot(
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
            raise ContractNotActiveError("last_updated is required for insert_option_snapshot")

        result = await database.optionsnapshot.create(
            data={
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
            }
        )

        Log.info(
            f"{curr_datetime} Inserted snapshot for {contract_ticker}: OI={snapshot.open_interest}"
        )
        Log.info(format_snapshot(contract_ticker, snapshot))

        return result
    except UniqueViolationError:
        Log.warn(f"{contract_ticker} at {last_updated_dt} has no new update on snapshot")
    except ContractNotActiveError as e:
        Log.warn(
            f"{curr_datetime}"
            f"{contract_ticker} is not active, Skipping inserting option snapshot: {e}"
        )
    except Exception as e:
        Log.error(
            f"{curr_datetime} Error inserting option snapshot for "
            f"{contract_ticker} at {last_updated_dt}: {e}"
        )


async def process_option_contracts(database: Prisma, contract: OptionsContract) -> Options:
    return await upsert_option_contract(database, contract)


async def process_option_snapshot(
    database: Prisma, contract_ticker: str, snapshot: OptionContractSnapshot
) -> OptionSnapshot:
    return await insert_option_snapshot(database, contract_ticker, snapshot)


if __name__ == "__main__":
    import asyncio

    async def main():
        await db.connect()
        contracts = await get_all_option_contracts(db)
        for contract in contracts:
            Log.info(f"Processing contract: {contract.ticker}")

        await db.disconnect()

    asyncio.run(main())
