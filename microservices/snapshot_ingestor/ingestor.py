"""Ingestor for option snapshots (market data, greeks, etc.)."""

import asyncio
import logging
import os
import traceback

import httpx

from microservices.option_ingestor.api import fetch_snapshots_batch
from microservices.option_ingestor.ingestor import OptionIngestor
from microservices.shared.decorator import (
    DATA_BASE_CONCURRENCY_LIMIT,
    bounded_async_sem,
    bounded_db_connection,
    traced_span_async,
)
from microservices.shared.errors import OptionTickerNeverActiveError, is_retryable_db_error
from microservices.shared.models import OptionContractSnapshot
from microservices.shared.observability import start_span_sync
from microservices.shared.util import format_snapshot, ns_to_datetime
from prisma import Json
from prisma.errors import ClientNotConnectedError, UniqueViolationError
from prisma.models import OptionSnapshot

logger = logging.getLogger(__name__)
DB_RETRY_MAX_ATTEMPTS = int(os.getenv("INGEST_DB_RETRY_MAX_ATTEMPTS", "3"))
DB_RETRY_BASE_DELAY_SECONDS = float(os.getenv("INGEST_DB_RETRY_BASE_DELAY_SECONDS", "0.5"))


class OptionSnapshotsIngestor(OptionIngestor):
    """Ingestor specifically for option snapshots (market data, greeks, etc.)."""

    @bounded_db_connection
    @traced_span_async(name="ingest_option_snapshots", attributes={"module": "ingestor"})
    async def ingest_option_snapshots(self):
        """Ingest option snapshots for all active contracts."""
        try:
            total_contracts = 0
            async for contracts_batch in self.option_retriever.stream_retrieve_active():
                logger.info("Processing batch of %s contracts...", len(contracts_batch))
                total_contracts += len(contracts_batch)
                snapshots = await fetch_snapshots_batch(contracts_batch)
                with start_span_sync(
                    "transform_snapshot_batch",
                    attributes={
                        "module": "TRANSFORM",
                        "contract_batch_size": len(contracts_batch),
                        "snapshot_result_count": len(snapshots),
                    },
                ):
                    if len(snapshots) != len(contracts_batch):
                        raise RuntimeError(
                            "Snapshot fetch result count mismatch: "
                            f"contracts_batch_size={len(contracts_batch)} "
                            f"snapshot_result_count={len(snapshots)}"
                        )
                    valid_contract_snapshots = [
                        (contract, snapshot)
                        for contract, snapshot in zip(contracts_batch, snapshots)
                        if snapshot is not None
                    ]
                logger.info(
                    "Fetched %s/%s snapshots successfully for current batch",
                    len(valid_contract_snapshots),
                    len(contracts_batch),
                )
                tasks = [
                    asyncio.create_task(self._upsert_option_snapshot(contract.ticker, snapshot))
                    for contract, snapshot in valid_contract_snapshots
                ]
                await asyncio.gather(*tasks)
            logger.info(
                f"All option snapshots processed successfully. "
                f"Total contracts processed: {total_contracts}"
            )
        except httpx.ConnectTimeout:
            logger.exception(
                "Option snapshots ingestion aborted due to Polygon connect timeout"
            )
            raise
        except httpx.RequestError as exc:
            logger.exception(
                "Option snapshots ingestion aborted due to network request error: %s",
                type(exc).__name__,
            )
            raise
        except Exception as e:
            logger.exception(
                "Error during option snapshots ingestion (%s): %r",
                type(e).__name__,
                e,
            )
            raise

    @bounded_async_sem(limit=DATA_BASE_CONCURRENCY_LIMIT)
    @traced_span_async(name="_upsert_option_snapshot", attributes={"module": "DB"})
    async def _upsert_option_snapshot(
        self,
        contract_ticker: str,
        snapshot: OptionContractSnapshot,
        max_retries: int = DB_RETRY_MAX_ATTEMPTS,
        base_delay_seconds: float = DB_RETRY_BASE_DELAY_SECONDS,
    ) -> "OptionSnapshot | None":
        """Upsert a single option snapshot into the database."""
        last_updated_raw = _snapshot_last_updated_raw(snapshot)
        last_updated_dt = ns_to_datetime(last_updated_raw) if last_updated_raw else None
        curr_datetime = self.ingest_time
        attempt = 0
        with start_span_sync(
            "transform_snapshot_payload",
            attributes={
                "module": "TRANSFORM",
                "option_ticker_name": contract_ticker,
            },
        ):
            greeks = _snapshot_greeks_json(snapshot)

        while attempt < max_retries:
            try:
                if last_updated_dt is None:
                    raise OptionTickerNeverActiveError("last_updated is required")
                payload = _build_snapshot_upsert_payload(
                    contract_ticker=contract_ticker,
                    snapshot=snapshot,
                    last_updated_dt=last_updated_dt,
                    curr_datetime=curr_datetime,
                    greeks=greeks,
                )
                result = await OptionSnapshot.prisma().upsert(
                    where={
                        "ticker_last_updated": {
                            "ticker": contract_ticker,
                            "last_updated": last_updated_dt,
                        }
                    },
                    data=payload,
                )
                logger.info(
                    f"{curr_datetime} Inserted snapshot for {contract_ticker}: "
                    f"OI={snapshot.open_interest}"
                )
                logger.info(format_snapshot(contract_ticker, snapshot))
                return result
            except Exception as e:
                should_retry = _handle_snapshot_upsert_error(
                    error=e,
                    context={
                        "contract_ticker": contract_ticker,
                        "last_updated_dt": last_updated_dt,
                        "curr_datetime": curr_datetime,
                        "attempt": attempt,
                    },
                    max_retries=max_retries,
                )
                if should_retry:
                    delay = base_delay_seconds * (2**attempt)
                    attempt += 1
                    logger.warning(
                        "Retrying snapshot upsert for %s after transient DB error in %.2fs",
                        contract_ticker,
                        delay,
                    )
                    await asyncio.sleep(delay)
                    continue
                return None


def _snapshot_last_updated_raw(snapshot: OptionContractSnapshot):
    if snapshot.day is None:
        return None
    return snapshot.day.last_updated


def _snapshot_greeks_json(snapshot: OptionContractSnapshot):
    if not snapshot.greeks:
        return None
    greeks_dict = {
        "delta": snapshot.greeks.delta if snapshot.greeks.delta is not None else None,
        "gamma": snapshot.greeks.gamma if snapshot.greeks.gamma is not None else None,
        "theta": snapshot.greeks.theta if snapshot.greeks.theta is not None else None,
        "vega": snapshot.greeks.vega if snapshot.greeks.vega is not None else None,
    }
    return Json(greeks_dict)


def _build_snapshot_upsert_payload(
    contract_ticker: str,
    snapshot: OptionContractSnapshot,
    last_updated_dt,
    curr_datetime,
    greeks,
) -> dict:
    open_interest = int(snapshot.open_interest) if snapshot.open_interest is not None else None
    volume = (
        int(snapshot.day.volume)
        if snapshot.day is not None and snapshot.day.volume is not None
        else None
    )
    last_price = snapshot.day.close if snapshot.day is not None else None
    day_open = snapshot.day.open if snapshot.day is not None else None
    day_close = snapshot.day.close if snapshot.day is not None else None
    day_change = snapshot.day.change_percent if snapshot.day is not None else None
    base_payload = {
        "open_interest": open_interest,
        "volume": volume,
        "implied_vol": snapshot.implied_volatility,
        "greeks": greeks if greeks is not None else None,
        "last_price": last_price,
        "last_updated": last_updated_dt,
        "last_crawled": curr_datetime,
        "day_open": day_open,
        "day_close": day_close,
        "day_change": day_change,
    }
    return {
        "create": {
            "ticker": contract_ticker,
            **base_payload,
        },
        "update": base_payload,
    }


def _handle_snapshot_upsert_error(
    error: Exception,
    context: dict,
    max_retries: int,
) -> bool:
    contract_ticker = context["contract_ticker"]
    last_updated_dt = context["last_updated_dt"]
    curr_datetime = context["curr_datetime"]
    attempt = context["attempt"]
    next_attempt = attempt + 1

    if isinstance(error, UniqueViolationError):
        logger.info("%s at %s has no new update on snapshot", contract_ticker, last_updated_dt)
        return False
    if isinstance(error, OptionTickerNeverActiveError):
        logger.info("%s is not active", contract_ticker)
        return False
    if isinstance(error, ClientNotConnectedError):
        logger.error(
            "Database connection error: %s. Retrying up to %s times...", error, max_retries
        )
        return next_attempt < max_retries
    if is_retryable_db_error(error):
        logger.error(
            "Transient database transport error for %s: %s (attempt %s/%s)",
            contract_ticker,
            type(error).__name__,
            next_attempt,
            max_retries,
        )
        return next_attempt < max_retries

    logger.error(
        f"{curr_datetime} Error inserting option snapshot for "
        f"{contract_ticker}: {error} (attempt {next_attempt}/{max_retries})"
    )
    if next_attempt < max_retries:
        return True

    logger.error(traceback.format_exc())
    logger.error("Failed to insert snapshot for %s after %s attempts", contract_ticker, max_retries)
    return False


__all__ = ["OptionSnapshotsIngestor"]
