from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class ExchangeRatesLatestOut(BaseModel):
    base_currency: str
    fetched_at: datetime
    rates: dict[str, Decimal]
