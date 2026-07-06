import logging
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import httpx

from app.config import settings
from app.db.session import SessionLocal
from app.models.exchange_rate_snapshot import ExchangeRateSnapshot

logger = logging.getLogger(__name__)


class ExchangeRateUnavailable(Exception):
    """Raised when no sufficiently fresh exchange rate can be obtained."""


def fetch_and_store_snapshot() -> None:
    """Fetch latest rates from frankfurter.dev and insert one snapshot row per currency.

    On any failure, logs and returns without writing partial data.
    """
    url = f"{settings.frankfurter_base_url}/latest"
    try:
        response = httpx.get(url, params={"base": settings.exchange_rate_base_currency}, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        base = data["base"]
        rates = data["rates"]
    except Exception:
        logger.exception("Failed to fetch exchange rates from frankfurter.dev")
        return

    now = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        for currency, rate in rates.items():
            db.add(
                ExchangeRateSnapshot(
                    id=uuid.uuid4(),
                    base_currency=base,
                    quote_currency=currency,
                    rate=Decimal(str(rate)),
                    fetched_at=now,
                    source="frankfurter.dev",
                )
            )
        db.commit()
        logger.info("Stored %d exchange rate snapshots (base=%s)", len(rates), base)
    except Exception:
        db.rollback()
        logger.exception("Failed to persist exchange rate snapshots; no rows written")
    finally:
        db.close()


def get_latest_rate(quote_currency: str) -> tuple[Decimal, uuid.UUID | None, datetime]:
    """Returns (rate, snapshot_id, fetched_at) for quote_currency vs. the base currency.

    Raises ExchangeRateUnavailable if no sufficiently fresh rate can be obtained.
    """
    if quote_currency == settings.exchange_rate_base_currency:
        return Decimal("1.0"), None, datetime.now(timezone.utc)

    staleness_cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.rate_staleness_hours)

    db = SessionLocal()
    try:
        row = (
            db.query(ExchangeRateSnapshot)
            .filter(ExchangeRateSnapshot.quote_currency == quote_currency)
            .order_by(ExchangeRateSnapshot.fetched_at.desc())
            .first()
        )

        if row is None or row.fetched_at < staleness_cutoff:
            fetch_and_store_snapshot()
            row = (
                db.query(ExchangeRateSnapshot)
                .filter(ExchangeRateSnapshot.quote_currency == quote_currency)
                .order_by(ExchangeRateSnapshot.fetched_at.desc())
                .first()
            )
            if row is None or row.fetched_at < staleness_cutoff:
                raise ExchangeRateUnavailable(f"No fresh exchange rate available for {quote_currency}")

        return row.rate, row.id, row.fetched_at
    finally:
        db.close()


def ensure_todays_snapshot() -> None:
    """On app startup, fetch immediately if no snapshot exists from today (UTC)."""
    today = datetime.now(timezone.utc).date()
    db = SessionLocal()
    try:
        latest = db.query(ExchangeRateSnapshot).order_by(ExchangeRateSnapshot.fetched_at.desc()).first()
    finally:
        db.close()

    if latest is None or latest.fetched_at.date() < today:
        logger.info("No exchange rate snapshot from today found; fetching now before serving traffic")
        fetch_and_store_snapshot()
