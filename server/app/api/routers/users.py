from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.currencies import validate_currency
from app.core.uploads import save_photo
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserOut

router = APIRouter()


def _to_user_out(user: User) -> UserOut:
    return UserOut(
        user_id=user.id,
        email=user.email,
        name=user.name,
        photo_url=user.photo_url,
        default_currency=user.default_currency,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)) -> UserOut:
    return _to_user_out(current_user)


@router.patch("/me", response_model=UserOut)
async def update_me(
    name: str | None = Form(None),
    default_currency: str | None = Form(None),
    photo_url: str | None = Form(None),
    photo: UploadFile | None = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserOut:
    if photo is not None and photo_url is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide either 'photo' or 'photo_url', not both",
        )

    if name is not None:
        current_user.name = name

    if default_currency is not None:
        try:
            current_user.default_currency = validate_currency(default_currency)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    if photo is not None:
        try:
            current_user.photo_url = await save_photo(photo)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    elif photo_url is not None:
        current_user.photo_url = photo_url

    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    return _to_user_out(current_user)
