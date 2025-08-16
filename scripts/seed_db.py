import os
import asyncio
from datetime import datetime, timedelta, timezone

from dotenv import dotenv_values

# Ensure DATABASE_URL is present for Prisma
vals = dotenv_values(os.path.join(os.path.dirname(__file__), '..', '.env'))
if vals.get('DATABASE_URL'):
    os.environ['DATABASE_URL'] = vals['DATABASE_URL']

from prisma import Prisma, Json  # type: ignore


async def upsert_option(db: Prisma, *, ticker: str, underlying: str, ctype: str, strike: float, exp: datetime):
    return await db.options.upsert(
        where={'ticker': ticker},
        data={
            'create': {
                'ticker': ticker,
                'underlying_ticker': underlying,
                'contract_type': ctype,
                'strike_price': float(strike),
                'expiration_date': exp,
            },
            'update': {
                'underlying_ticker': underlying,
                'contract_type': ctype,
                'strike_price': float(strike),
                'expiration_date': exp,
            },
        },
    )


async def upsert_snapshot(db: Prisma, *, option_id: int, when: datetime, oi: int | None, vol: int | None,
                          iv: float | None, last_price: float | None, day_open: float | None,
                          day_close: float | None, day_change: float | None):
    data = {
        'open_interest': oi,
        'volume': vol,
        'implied_vol': iv,
        'greeks': Json({'delta': 0.5, 'gamma': 0.1, 'theta': -0.02, 'vega': 0.15}),
        'last_price': last_price,
        'last_updated': when,
        'last_crawled': datetime.now(timezone.utc),
        'day_open': day_open,
        'day_close': day_close,
        'day_change': day_change,
        'option': {'connect': {'id': option_id}},
    }
    return await db.optionsnapshot.upsert(
        where={'optionId_last_updated': {'optionId': option_id, 'last_updated': when}},
        data={'create': data, 'update': data},
    )


async def main():
    db = Prisma()
    await db.connect()

    try:
        tz = timezone.utc
        # Seed two options
        aapl = await upsert_option(
            db,
            ticker='AAPL250919C00190000',
            underlying='AAPL',
            ctype='CALL',
            strike=190.0,
            exp=datetime(2025, 9, 19, 20, 0, 0, tzinfo=tz),
        )
        tsla = await upsert_option(
            db,
            ticker='TSLA250919P00150000',
            underlying='TSLA',
            ctype='PUT',
            strike=150.0,
            exp=datetime(2025, 9, 19, 20, 0, 0, tzinfo=tz),
        )

        now = datetime.now(tz).replace(microsecond=0)
        times = [now - timedelta(minutes=2), now - timedelta(minutes=1), now]

        # AAPL snapshots
        for i, t in enumerate(times):
            await upsert_snapshot(
                db,
                option_id=aapl.id,
                when=t,
                oi=1000 + i * 25,
                vol=5000 + i * 100,
                iv=0.30 + i * 0.01,
                last_price=2.50 + i * 0.1,
                day_open=2.40,
                day_close=2.55 + i * 0.1,
                day_change=0.02 + i * 0.005,
            )

        # TSLA snapshots
        for i, t in enumerate(times):
            await upsert_snapshot(
                db,
                option_id=tsla.id,
                when=t,
                oi=800 + i * 20,
                vol=4200 + i * 120,
                iv=0.55 + i * 0.015,
                last_price=3.10 + i * 0.12,
                day_open=3.00,
                day_close=3.22 + i * 0.12,
                day_change=-0.01 + i * 0.004,
            )

        print('Seed complete:')
        print('  Option IDs:', aapl.id, tsla.id)
        print('  Snapshots inserted for each at:', ', '.join([t.isoformat() for t in times]))
    finally:
        await db.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
