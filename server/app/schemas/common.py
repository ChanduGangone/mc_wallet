from typing import Annotated

from pydantic import AfterValidator

from app.core.currencies import validate_currency

Currency = Annotated[str, AfterValidator(validate_currency)]
