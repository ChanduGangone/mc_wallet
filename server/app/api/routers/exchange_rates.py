from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.exchange_rate_snapshot import ExchangeRateSnapshot
from app.schemas.exchange_rate import ExchangeRatesLatestOut

router = APIRouter()


@router.get("/latest", response_model=ExchangeRatesLatestOut)
def get_latest_rates(db: Session = Depends(get_db)) -> ExchangeRatesLatestOut:
    subq = (
        db.query(
            ExchangeRateSnapshot.quote_currency,
            func.max(ExchangeRateSnapshot.fetched_at).label("max_fetched_at"),
        )
        .group_by(ExchangeRateSnapshot.quote_currency)
        .subquery()
    )
    rows = (
        db.query(ExchangeRateSnapshot)
        .join(
            subq,
            (ExchangeRateSnapshot.quote_currency == subq.c.quote_currency)
            & (ExchangeRateSnapshot.fetched_at == subq.c.max_fetched_at),
        )
        .all()
    )
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No exchange rate data available")

    return ExchangeRatesLatestOut(
        base_currency=rows[0].base_currency,
        fetched_at=max(r.fetched_at for r in rows),
        rates={r.quote_currency: r.rate for r in rows},
    )
