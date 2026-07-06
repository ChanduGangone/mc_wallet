import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import Currency


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str | None = None
    default_currency: Currency | None = None


class SignupOut(BaseModel):
    user_id: uuid.UUID
    email: EmailStr
    name: str | None
    default_currency: str
    created_at: datetime


class UserOut(BaseModel):
    user_id: uuid.UUID
    email: EmailStr
    name: str | None
    photo_url: str | None
    default_currency: str
    created_at: datetime
    updated_at: datetime


class UserUpdate(BaseModel):
    name: str | None = None
    photo_url: str | None = None
    default_currency: Currency | None = None
