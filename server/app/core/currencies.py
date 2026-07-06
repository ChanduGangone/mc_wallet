ISO4217_SUBSET: frozenset[str] = frozenset(
    {
        "USD", "EUR", "GBP", "INR", "JPY", "AUD", "CAD", "CHF", "CNY", "SGD",
        "AED", "ZAR", "NZD", "SEK", "NOK", "DKK", "HKD", "KRW", "MXN", "BRL",
    }
)


def validate_currency(code: str) -> str:
    code_upper = code.upper()
    if code_upper not in ISO4217_SUBSET:
        raise ValueError(f"Unsupported currency code: {code}")
    return code_upper
