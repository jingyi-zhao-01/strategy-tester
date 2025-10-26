"""Ingestor for option snapshots (market data, greeks, etc.)."""

import asyncio
import traceback

from lib.observability import Log
from options.errors import OptionTickerNeverActiveError
from options.util import (
    format_snapshot,
    ns_to_datetime,
)
from prisma import Json
from prisma.errors import ClientNotConnectedError, UniqueViolationError
from prisma.models import OptionSnapshot

from ..api.options import fetch_snapshots_batch
from ..decorator import (
    DATA_BASE_CONCURRENCY_LIMIT,
    bounded_async_sem,
    bounded_db_connection,
    traced_span_async,
)
from ..models import OptionContractSnapshot
from .option_contract_ingestor import OptionIngestor


class OptionSnapshotsIngestor(OptionIngestor):
    """Ingestor specifically for option snapshots (market data, greeks, etc.)."""

    @bounded_db_connection
    @traced_span_async(name="ingest_option_snapshots", attributes={"module": "ingestor"})
    async def ingest_option_snapshots(self):
        """Ingest option snapshots for all active contracts."""
        try:
            total_contracts = 0
            async for contracts_batch in self.option_retriever.stream_retrieve_active():
                Log.info(f"Processing batch of {len(contracts_batch)} contracts...")
                total_contracts += len(contracts_batch)
                snapshots = await fetch_snapshots_batch(contracts_batch)
                await asyncio.gather(
                    *[
                        self._upsert_option_snapshot(contract.ticker, snapshot)
                        for contract, snapshot in zip(contracts_batch, snapshots, strict=True)
                    ]
                )
            Log.info(
                f"All option snapshots processed successfully. "
                f"Total contracts processed: {total_contracts}"
            )
        except Exception as e:
            Log.error(f"Error during option snapshots ingestion: {e}\n{traceback.format_exc()}")
            # Do not re-raise to avoid duplicate logging and empty error messages

    @bounded_async_sem(limit=DATA_BASE_CONCURRENCY_LIMIT)
    @traced_span_async(name="_upsert_option_snapshot", attributes={"module": "DB"})
    async def _upsert_option_snapshot(
        self,
        contract_ticker: str,
        snapshot: OptionContractSnapshot,
        max_retries: int = 1,
        delay: float = 1.0,
    ) -> "OptionSnapshot | None":
        """Upsert a single option snapshot into the database."""
        last_updated_raw = (
            snapshot.day.last_updated
            if snapshot.day is not None and snapshot.day.last_updated
            else None
        )
        last_updated_dt = ns_to_datetime(last_updated_raw) if last_updated_raw else None
        curr_datetime = self.ingest_time
        attempt = 0

        greeks = None
        if snapshot.greeks:
            greeks_dict = {
                "delta": snapshot.greeks.delta if snapshot.greeks.delta is not None else None,
                "gamma": snapshot.greeks.gamma if snapshot.greeks.gamma is not None else None,
                "theta": snapshot.greeks.theta if snapshot.greeks.theta is not None else None,
                "vega": snapshot.greeks.vega if snapshot.greeks.vega is not None else None,
            }
            greeks = Json(greeks_dict)

        while attempt < max_retries:
            try:
                if last_updated_dt is None:
                    raise OptionTickerNeverActiveError("last_updated is required")
                result = await OptionSnapshot.prisma().upsert(
                    where={
                        "ticker_last_updated": {
                            "ticker": contract_ticker,
                            "last_updated": last_updated_dt,
                        }
                    },
                    data={
                        "create": {
                            "ticker": contract_ticker,
                            "open_interest": (
                                int(snapshot.open_interest)
                                if snapshot.open_interest is not None
                                else None
                            ),
                            "volume": (
                                int(snapshot.day.volume)
                                if snapshot.day is not None and snapshot.day.volume is not None
                                else None
                            ),
                            "implied_vol": snapshot.implied_volatility,
                            "greeks": greeks if greeks is not None else None,
                            "last_price": (
                                snapshot.day.close if snapshot.day is not None else None
                            ),
                            "last_updated": last_updated_dt,
                            "last_crawled": curr_datetime,
                            "day_open": (snapshot.day.open if snapshot.day is not None else None),
                            "day_close": (snapshot.day.close if snapshot.day is not None else None),
                            "day_change": (
                                snapshot.day.change_percent if snapshot.day is not None else None
                            ),
                        },
                        "update": {
                            "open_interest": (
                                int(snapshot.open_interest)
                                if snapshot.open_interest is not None
                                else None
                            ),
                            "volume": (
                                int(snapshot.day.volume)
                                if snapshot.day is not None and snapshot.day.volume is not None
                                else None
                            ),
                            "implied_vol": snapshot.implied_volatility,
                            "greeks": greeks if greeks is not None else None,
                            "last_price": (
                                snapshot.day.close if snapshot.day is not None else None
                            ),
                            "last_updated": last_updated_dt,
                            "last_crawled": curr_datetime,
                            "day_open": (snapshot.day.open if snapshot.day is not None else None),
                            "day_close": (snapshot.day.close if snapshot.day is not None else None),
                            "day_change": (
                                snapshot.day.change_percent if snapshot.day is not None else None
                            ),
                        },
                    },
                )
                Log.info(
                    f"{curr_datetime} Inserted snapshot for {contract_ticker}: "
                    f"OI={snapshot.open_interest}"
                )
                Log.info(format_snapshot(contract_ticker, snapshot))
                return result
            except UniqueViolationError:
                Log.info(f"{contract_ticker} at {last_updated_dt} has no new update on snapshot")
                break
            except OptionTickerNeverActiveError:
                Log.info(f"{contract_ticker} is not active")
                break
            except ClientNotConnectedError as e:
                Log.error(f"Database connection error: {e}. Retrying up to {max_retries} times...")
                break
            except Exception as e:
                attempt += 1
                Log.error(
                    f"{curr_datetime} Error inserting option snapshot for "
                    f"{contract_ticker}: {e} (attempt {attempt}/{max_retries})"
                )
                if attempt < max_retries:
                    await asyncio.sleep(delay)
                else:
                    Log.error(traceback.format_exc())
                    Log.error(
                        f"Failed to insert snapshot for {contract_ticker} after "
                        f"{max_retries} attempts"
                    )


__all__ = ["OptionSnapshotsIngestor"]
