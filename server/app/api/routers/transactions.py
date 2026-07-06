from datetime import date, datetime, time, timedelta, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.transaction import Transaction
from app.models.user import User
from app.models.wallet import Wallet
from app.schemas.common import Currency
from app.schemas.transaction import TransactionListOut, TransactionOut

router = APIRouter()


def _to_transaction_out(txn: Transaction) -> TransactionOut:
    return TransactionOut(
        transaction_id=txn.id,
        type=txn.type,
        from_wallet_id=txn.from_wallet_id,
        to_wallet_id=txn.to_wallet_id,
        amount=txn.amount,
        from_currency=txn.from_currency,
        converted_amount=txn.converted_amount,
        to_currency=txn.to_currency,
        from_rate_snapshot_id=txn.from_rate_snapshot_id,
        to_rate_snapshot_id=txn.to_rate_snapshot_id,
        status=txn.status,
        created_at=txn.created_at,
    )


@router.get("", response_model=TransactionListOut)
def list_transactions(
    type_: Literal["credit", "debit", "transfer"] | None = Query(None, alias="type"),
    currency: Annotated[Currency | None, Query()] = None,
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TransactionListOut:
    wallet_ids = [w.id for w in db.query(Wallet.id).filter(Wallet.user_id == current_user.id).all()]

    query = db.query(Transaction).filter(
        or_(Transaction.from_wallet_id.in_(wallet_ids), Transaction.to_wallet_id.in_(wallet_ids))
    )

    if type_ is not None:
        query = query.filter(Transaction.type == type_)

    if currency is not None:
        query = query.filter(or_(Transaction.from_currency == currency, Transaction.to_currency == currency))

    if start_date is not None:
        query = query.filter(Transaction.created_at >= datetime.combine(start_date, time.min, tzinfo=timezone.utc))

    if end_date is not None:
        end_exclusive = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc)
        query = query.filter(Transaction.created_at < end_exclusive)

    total = query.count()
    items = query.order_by(Transaction.created_at.desc()).offset(offset).limit(limit).all()

    return TransactionListOut(
        total=total,
        limit=limit,
        offset=offset,
        items=[_to_transaction_out(t) for t in items],
    )
