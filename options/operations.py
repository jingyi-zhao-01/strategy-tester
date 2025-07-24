from datetime import datetime
from prisma import Prisma
from prisma.models import Options, OptionSnapshot
from models import OptionsContract, OptionContractSnapshot


db = Prisma(auto_register=True)


# TODO: Upsert Bulk ?
# TODO: advantage of using ContextManager ?


def ns_to_datetime(ns: int) -> datetime:
    return datetime.fromtimestamp(ns / 1e9)


class PrismaConnection:
    def __init__(self, db: Prisma):
        self.db = db

    async def __aenter__(self):
        await self.db.connect()
        return self.db

    async def __aexit__(self, exc_type, exc, tb):
        await self.db.disconnect()


async def upsert_option_contract(db: Prisma, contract: OptionsContract) -> Options:
    """
    Upsert an option contract into the database.
    If the contract exists (by ticker), update it, otherwise create it.
    """
    if isinstance(contract.expiration_date, str):
        year, month, day = map(int, contract.expiration_date.split("-"))
        expiration_dt = datetime(year, month, day)
    else:
        expiration_dt = contract.expiration_date

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


async def upsert_option_snapshot(
    db: Prisma, contract_ticker: str, snapshot: OptionContractSnapshot
) -> OptionSnapshot:
    """
    Upsert an option snapshot into the database.
    Indexed by ticker and last_updated.
    Links to the parent option contract via ticker.
    """
    last_updated_raw = snapshot.day.last_updated if snapshot.day.last_updated else None
    last_updated_dt = ns_to_datetime(last_updated_raw) if last_updated_raw else None

    return await db.optionsnapshot.upsert(
        where={
            "ticker_last_updated": {
                "ticker": contract_ticker,
                "last_updated": last_updated_dt,
            }
        },
        data={
            "create": {
                "ticker": contract_ticker,
                "open_interest": snapshot.open_interest,
                "volume": snapshot.day.volume if snapshot.day else None,
                "implied_volatility": snapshot.implied_volatility,
                "last_price": snapshot.day.close if snapshot.day else None,
                "last_updated": last_updated_dt,
                "day_open": snapshot.day.open if snapshot.day else None,
                "day_close": snapshot.day.close if snapshot.day else None,
                "day_change": snapshot.day.change_percent if snapshot.day else None,
                "option": {"connect": {"ticker": contract_ticker}},
            },
            "update": {
                "ticker": contract_ticker,
                "open_interest": snapshot.open_interest,
                "volume": snapshot.day.volume if snapshot.day else None,
                "implied_volatility": snapshot.implied_volatility,
                "last_price": snapshot.day.close if snapshot.day else None,
                "last_updated": last_updated_dt,
                "day_open": snapshot.day.open if snapshot.day else None,
                "day_close": snapshot.day.close if snapshot.day else None,
                "day_change": snapshot.day.change_percent if snapshot.day else None,
                "option": {"connect": {"ticker": contract_ticker}},
            },
        },
    )


async def process_option_contract(contract: OptionsContract) -> Options:
    async with PrismaConnection(db) as db_instance:
        return await upsert_option_contract(db_instance, contract)


async def process_option_snapshot(
    contract_ticker: str, snapshot: OptionContractSnapshot
) -> OptionSnapshot:
    async with PrismaConnection(db) as db_instance:
        return await upsert_option_snapshot(db_instance, contract_ticker, snapshot)
