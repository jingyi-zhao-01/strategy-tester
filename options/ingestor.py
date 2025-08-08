import asyncio
import traceback

from lib import Log
from options.api.options import Fetcher, fetch_snapshots_batch, get_contract_within_price_range
from options.errors import OptionTickerNeverActiveError
from options.util import (
    format_snapshot,
    get_current_datetime,
    ns_to_datetime,
    option_expiration_date_to_datetime,
)
from prisma import Json
from prisma.errors import ClientNotConnectedError, UniqueViolationError
from prisma.models import Options, OptionSnapshot

from .decorator import (
    bounded_async_sem,
    bounded_db_connection,
)
from .models import OptionContractSnapshot, OptionIngestParams, OptionsContract
from .retriever import OptionRetriever


class OptionIngestor:
    def __init__(self, option_retriever=None):
        self.ingest_time = get_current_datetime()

        if option_retriever is None:
            raise ValueError("option_retriever must be provided")

        self.option_retriever: OptionRetriever = option_retriever.with_ingest_time(self.ingest_time)

    @bounded_db_connection
    async def ingest_options(self, underlying_assets: list[OptionIngestParams]):
        for target in underlying_assets:
            underlying_asset = target.underlying_asset
            price_range = target.price_range
            year_range = target.year_range
            core = Fetcher(underlying_asset)
            calls = core.get_call_contracts()
            puts = core.get_put_contracts()

            contracts = calls + puts
            Log.info(f"Total contracts found for {underlying_asset}: {len(contracts)}")
            if not contracts:
                Log.warn(f"No UnExpired contracts found for {underlying_asset}")
                continue

            contracts_within_range = get_contract_within_price_range(
                contracts, price_range, year_range
            )
            Log.info(
                f"Contracts within price range for {underlying_asset}: "
                f"{len(contracts_within_range)}"
            )

            await asyncio.gather(
                *[self._upsert_option_contract(contract) for contract in contracts_within_range]
            )
            Log.info(f"All contracts for {underlying_asset} processed successfully")

    @bounded_db_connection
    async def ingest_option_snapshots(self):
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

    async def _retrieve_all_option_contracts(self) -> list[Options]:
        try:
            contracts = await Options.prisma().find_many()
            Log.info(f"Retrieved {len(contracts)} option contracts from the database.")
            return contracts
        except Exception as e:
            Log.error(f"Error fetching option contracts: {e}")
            return []

    @bounded_async_sem(limit=200)
    async def _upsert_option_contract(self, contract: OptionsContract) -> Options:
        expiration_dt = option_expiration_date_to_datetime(str(contract.expiration_date))
        try:
            Log.info(
                f"Upserting contract: {contract.ticker}, "
                f"Strike: {contract.strike_price}, "
                f"Expiration: {expiration_dt}, "
                f"Type: {contract.contract_type}"
            )
            return await Options.prisma().upsert(
                where={"ticker": str(contract.ticker)},
                data={
                    "create": {
                        "ticker": str(contract.ticker),
                        "underlying_ticker": str(contract.underlying_ticker),
                        "strike_price": (
                            float(contract.strike_price)
                            if contract.strike_price is not None
                            else 0.0
                        ),
                        "expiration_date": expiration_dt,
                        "contract_type": "CALL" if contract.contract_type == "call" else "PUT",
                    },
                    "update": {
                        "underlying_ticker": str(contract.underlying_ticker),
                        "strike_price": (
                            float(contract.strike_price)
                            if contract.strike_price is not None
                            else 0.0
                        ),
                        "expiration_date": expiration_dt,
                        "contract_type": "CALL" if contract.contract_type == "call" else "PUT",
                    },
                },
            )
        except Exception as e:
            Log.error(f"Error upserting contract {contract.ticker}: {e} ({type(e).__name__})")
            Log.error(traceback.format_exc())
            raise

    @bounded_async_sem(limit=200)
    async def _upsert_option_snapshot(
        self,
        contract_ticker: str,
        snapshot: OptionContractSnapshot,
        max_retries: int = 1,
        delay: float = 1.0,
    ) -> OptionSnapshot | None:
        last_updated_raw = (
            snapshot.day.last_updated
            if snapshot.day is not None and snapshot.day.last_updated
            else None
        )
        last_updated_dt = ns_to_datetime(last_updated_raw) if last_updated_raw else None
        curr_datetime = self.ingest_time
        attempt = 0

        # Parse Greeks data

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
                            "option": {"connect": {"ticker": contract_ticker}},
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
                            "option": {"connect": {"ticker": contract_ticker}},
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
                # TODO: figure out a way inccacse database connecting error
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


__all__ = ["OptionIngestor"]
