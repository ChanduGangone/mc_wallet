import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.common import Currency


class WalletOut(BaseModel):
    wallet_id: uuid.UUID
    currency: str
    balance: Decimal
    created_at: datetime


class CreditRequest(BaseModel):
    amount: Decimal = Field(gt=0)
    currency: Currency


class CreditResponse(BaseModel):
    transaction_id: uuid.UUID
    wallet_id: uuid.UUID
    new_balance: Decimal
    converted_amount: Decimal
    to_rate_snapshot_id: uuid.UUID | None


class DebitRequest(BaseModel):
    amount: Decimal = Field(gt=0)


class DebitResponse(BaseModel):
    transaction_id: uuid.UUID
    wallet_id: uuid.UUID
    new_balance: Decimal
