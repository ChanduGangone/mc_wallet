import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class TransactionOut(BaseModel):
    transaction_id: uuid.UUID
    type: str
    from_wallet_id: uuid.UUID | None
    to_wallet_id: uuid.UUID | None
    amount: Decimal
    from_currency: str
    converted_amount: Decimal | None
    to_currency: str | None
    from_rate_snapshot_id: uuid.UUID | None
    to_rate_snapshot_id: uuid.UUID | None
    status: str
    created_at: datetime


class TransactionListOut(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[TransactionOut]
