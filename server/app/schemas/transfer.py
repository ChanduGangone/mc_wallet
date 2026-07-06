import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.common import Currency


class TransferRequest(BaseModel):
    from_wallet_id: uuid.UUID
    to_user_id: uuid.UUID
    to_currency: Currency | None = None
    amount: Decimal = Field(gt=0)


class TransferResponse(BaseModel):
    transaction_id: uuid.UUID
    from_wallet_id: uuid.UUID
    to_wallet_id: uuid.UUID
    amount: Decimal
    from_currency: str
    converted_amount: Decimal
    to_currency: str
    from_rate_snapshot_id: uuid.UUID | None
    to_rate_snapshot_id: uuid.UUID | None
    status: str
    created_at: datetime
