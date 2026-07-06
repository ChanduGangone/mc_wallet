import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

TransactionType = Literal["credit", "debit", "transfer"]
TransactionStatus = Literal["pending", "completed", "failed"]

TRANSACTION_TYPES = ("credit", "debit", "transfer")
TRANSACTION_STATUSES = ("pending", "completed", "failed")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type: Mapped[TransactionType] = mapped_column(String(20), nullable=False)

    from_wallet_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("wallets.id"), nullable=True, index=True
    )
    to_wallet_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("wallets.id"), nullable=True, index=True
    )

    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    from_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    converted_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    to_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)

    from_rate_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("exchange_rate_snapshots.id"), nullable=True
    )
    to_rate_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("exchange_rate_snapshots.id"), nullable=True
    )

    status: Mapped[TransactionStatus] = mapped_column(String(20), nullable=False, server_default="completed")
    idempotency_key: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    from_wallet: Mapped["Wallet | None"] = relationship(foreign_keys=[from_wallet_id])
    to_wallet: Mapped["Wallet | None"] = relationship(foreign_keys=[to_wallet_id])

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_transactions_amount_positive"),
        CheckConstraint(f"type IN {TRANSACTION_TYPES}", name="ck_transactions_type"),
        CheckConstraint(f"status IN {TRANSACTION_STATUSES}", name="ck_transactions_status"),
        Index("ix_transactions_from_wallet_id_created_at", "from_wallet_id", "created_at"),
        Index("ix_transactions_to_wallet_id_created_at", "to_wallet_id", "created_at"),
    )
