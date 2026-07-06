import uuid
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_owned_wallet
from app.core.exchange_rates import ExchangeRateUnavailable, get_latest_rate
from app.db.session import get_db
from app.models.transaction import Transaction
from app.models.user import User
from app.models.wallet import Wallet
from app.schemas.transfer import TransferRequest, TransferResponse

router = APIRouter()


def _resolve_or_create_wallet(db: Session, user_id: uuid.UUID, currency: str) -> Wallet:
    wallet = db.query(Wallet).filter(Wallet.user_id == user_id, Wallet.currency == currency).first()
    if wallet is not None:
        return wallet

    wallet = Wallet(user_id=user_id, currency=currency, balance=Decimal("0"))
    db.add(wallet)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        wallet = db.query(Wallet).filter(Wallet.user_id == user_id, Wallet.currency == currency).one()
    else:
        db.refresh(wallet)
    return wallet


def _lock_two_wallets(db: Session, id_a: uuid.UUID, id_b: uuid.UUID) -> tuple[Wallet, Wallet]:
    """Locks both wallet rows in ascending-id order to prevent deadlocks under concurrent transfers.

    Uses populate_existing() because from_wallet/to_wallet may already be in the session's
    identity map (from the earlier unlocked fetch) — without it, SQLAlchemy would silently
    return the stale cached object instead of refreshing it from the now-locked row, causing
    the balance check/mutation below to operate on stale data despite holding the lock.
    """
    lo, hi = (id_a, id_b) if id_a < id_b else (id_b, id_a)

    wallet_lo = db.execute(
        select(Wallet).where(Wallet.id == lo).with_for_update().execution_options(populate_existing=True)
    ).scalar_one()
    wallet_hi = db.execute(
        select(Wallet).where(Wallet.id == hi).with_for_update().execution_options(populate_existing=True)
    ).scalar_one()

    return (wallet_lo, wallet_hi) if id_a < id_b else (wallet_hi, wallet_lo)


def _transfer_response(txn: Transaction) -> TransferResponse:
    return TransferResponse(
        transaction_id=txn.id,
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


@router.post("", response_model=TransferResponse, status_code=status.HTTP_201_CREATED)
def create_transfer(
    body: TransferRequest,
    response: Response,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TransferResponse:
    from_wallet = get_owned_wallet(body.from_wallet_id, current_user, db)

    existing = db.query(Transaction).filter(Transaction.idempotency_key == idempotency_key).first()
    if existing is not None:
        response.status_code = status.HTTP_200_OK
        return _transfer_response(existing)

    receiver = db.query(User).filter(User.email == body.to_email).first()
    if receiver is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No user found with that email")

    to_currency = body.to_currency or receiver.default_currency
    to_wallet = _resolve_or_create_wallet(db, receiver.id, to_currency)

    if to_wallet.id == from_wallet.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Cannot transfer to the same wallet"
        )

    locked_from, locked_to = _lock_two_wallets(db, from_wallet.id, to_wallet.id)

    if locked_from.balance < body.amount:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Insufficient balance")

    from_currency = locked_from.currency
    from_rate_snapshot_id: uuid.UUID | None = None
    to_rate_snapshot_id: uuid.UUID | None = None

    if from_currency == to_currency:
        converted_amount = body.amount
    else:
        try:
            from_rate, from_rate_snapshot_id, _ = get_latest_rate(from_currency)
            to_rate, to_rate_snapshot_id, _ = get_latest_rate(to_currency)
        except ExchangeRateUnavailable as e:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))

        cross_rate = to_rate / from_rate
        converted_amount = (body.amount * cross_rate).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    locked_from.balance -= body.amount
    locked_to.balance += converted_amount

    txn = Transaction(
        type="transfer",
        from_wallet_id=locked_from.id,
        to_wallet_id=locked_to.id,
        amount=body.amount,
        from_currency=from_currency,
        converted_amount=converted_amount,
        to_currency=to_currency,
        from_rate_snapshot_id=from_rate_snapshot_id,
        to_rate_snapshot_id=to_rate_snapshot_id,
        idempotency_key=idempotency_key,
    )
    db.add(txn)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.query(Transaction).filter(Transaction.idempotency_key == idempotency_key).one()
        response.status_code = status.HTTP_200_OK
        return _transfer_response(existing)

    db.refresh(txn)
    return _transfer_response(txn)
