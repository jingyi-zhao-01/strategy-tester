from datetime import datetime
from prisma import Prisma
from models.option_models import OptionSymbolComponents


async def save_option_snapshot(
    db: Prisma, symbol_components: OptionSymbolComponents, snapshot_data: dict
) -> None:
    """
    Save option snapshot data to the database
    """
    await db.optionsnapshot.create(
        data={
            "ticker": f"O:{symbol_components.underlying}{symbol_components.expiration.strftime('%y%m%d')}{'C' if symbol_components.contract_type == 'CALL' else 'P'}{int(symbol_components.strike * 1000):08d}",
            "underlying": symbol_components.underlying,
            "strikePrice": symbol_components.strike,
            "expirationDate": symbol_components.expiration,
            "contractType": symbol_components.contract_type,
            "openInterest": snapshot_data.get("open_interest"),
            "volume": snapshot_data.get("day", {}).get("volume"),
            "impliedVol": snapshot_data.get("implied_volatility"),
            "lastPrice": snapshot_data.get("day", {}).get("close"),
            "dayOpen": snapshot_data.get("day", {}).get("open"),
            "dayClose": snapshot_data.get("day", {}).get("close"),
            "dayChange": snapshot_data.get("day", {}).get("change_percent"),
        }
    )


async def get_snapshots_by_date_range(
    db: Prisma, start_date: datetime, end_date: datetime, underlying: str = None
) -> list:
    """
    Get option snapshots within a date range
    """
    conditions = {"expirationDate": {"gte": start_date, "lte": end_date}}

    if underlying:
        conditions["underlying"] = underlying

    return await db.optionsnapshot.find_many(
        where=conditions, order={"openInterest": "desc"}
    )
