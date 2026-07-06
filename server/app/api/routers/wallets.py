import uuid
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_owned_wallet
from app.core.exchange_rates import ExchangeRateUnavailable, get_latest_rate
from app.db.session import get_db
from app.models.transaction import Transaction
from app.models.user import User
from app.models.wallet import Wallet
from app.schemas.wallet import (
    CreditRequest,
    CreditResponse,
    DebitRequest,
    DebitResponse,
    WalletOut,
)

router = APIRouter()


def _to_wallet_out(wallet: Wallet) -> WalletOut:
    return WalletOut(
        wallet_id=wallet.id,
        currency=wallet.currency,
        balance=wallet.balance,
        created_at=wallet.created_at,
    )


def _credit_response(txn: Transaction, balance: Decimal) -> CreditResponse:
    return CreditResponse(
        transaction_id=txn.id,
        wallet_id=txn.to_wallet_id,
        new_balance=balance,
        converted_amount=txn.converted_amount if txn.converted_amount is not None else txn.amount,
        to_rate_snapshot_id=txn.to_rate_snapshot_id,
    )


def _debit_response(txn: Transaction, balance: Decimal) -> DebitResponse:
    return DebitResponse(transaction_id=txn.id, wallet_id=txn.from_wallet_id, new_balance=balance)


@router.get("", response_model=list[WalletOut])
def list_wallets(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[WalletOut]:
    wallets = db.query(Wallet).filter(Wallet.user_id == current_user.id).order_by(Wallet.created_at).all()
    return [_to_wallet_out(w) for w in wallets]


@router.post("/{wallet_id}/credit", response_model=CreditResponse)
def credit_wallet(
    wallet_id: uuid.UUID,
    body: CreditRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CreditResponse:
    wallet = get_owned_wallet(wallet_id, current_user, db)

    existing = db.query(Transaction).filter(Transaction.idempotency_key == idempotency_key).first()
    if existing is not None:
        current_balance = db.get(Wallet, wallet_id).balance
        return _credit_response(existing, current_balance)

    from_currency = body.currency
    to_currency = wallet.currency
    from_rate_snapshot_id: uuid.UUID | None = None
    to_rate_snapshot_id: uuid.UUID | None = None

    if from_currency == to_currency:
        converted_amount_db: Decimal | None = None
        credit_amount = body.amount
    else:
        try:
            from_rate, from_rate_snapshot_id, _ = get_latest_rate(from_currency)
            to_rate, to_rate_snapshot_id, _ = get_latest_rate(to_currency)
        except ExchangeRateUnavailable as e:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))

        cross_rate = to_rate / from_rate
        converted_amount_db = (body.amount * cross_rate).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        credit_amount = converted_amount_db

    stmt = (
        update(Wallet)
        .where(Wallet.id == wallet.id)
        .values(balance=Wallet.balance + credit_amount)
        .returning(Wallet.balance)
    )
    new_balance = db.execute(stmt).scalar_one()

    txn = Transaction(
        type="credit",
        from_wallet_id=None,
        to_wallet_id=wallet.id,
        amount=body.amount,
        from_currency=from_currency,
        converted_amount=converted_amount_db,
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
        current_balance = db.get(Wallet, wallet_id).balance
        return _credit_response(existing, current_balance)

    db.refresh(txn)
    return _credit_response(txn, new_balance)


@router.post("/{wallet_id}/debit", response_model=DebitResponse)
def debit_wallet(
    wallet_id: uuid.UUID,
    body: DebitRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DebitResponse:
    wallet = get_owned_wallet(wallet_id, current_user, db)

    existing = db.query(Transaction).filter(Transaction.idempotency_key == idempotency_key).first()
    if existing is not None:
        current_balance = db.get(Wallet, wallet_id).balance
        return _debit_response(existing, current_balance)

    stmt = (
        update(Wallet)
        .where(Wallet.id == wallet.id, Wallet.balance >= body.amount)
        .values(balance=Wallet.balance - body.amount)
        .returning(Wallet.balance)
    )
    row = db.execute(stmt).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Insufficient balance")
    new_balance = row[0]

    txn = Transaction(
        type="debit",
        from_wallet_id=wallet.id,
        to_wallet_id=None,
        amount=body.amount,
        from_currency=wallet.currency,
        converted_amount=None,
        to_currency=None,
        from_rate_snapshot_id=None,
        to_rate_snapshot_id=None,
        idempotency_key=idempotency_key,
    )
    db.add(txn)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.query(Transaction).filter(Transaction.idempotency_key == idempotency_key).one()
        current_balance = db.get(Wallet, wallet_id).balance
        return _debit_response(existing, current_balance)

    db.refresh(txn)
    return _debit_response(txn, new_balance)
