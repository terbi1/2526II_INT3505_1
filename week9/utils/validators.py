"""
core/validators.py
------------------
Reusable field-level validators used by v1 and v2 schemas.
"""

from utils.database import SUPPORTED_CURRENCIES, PAYMENT_METHODS


def validate_amount_float(value) -> list[str]:
    """V1 style: amount as float/int."""
    errors = []
    if not isinstance(value, (int, float)):
        errors.append("Must be a number (float or int).")
    elif value <= 0:
        errors.append("Must be greater than 0.")
    elif value > 1_000_000_000:
        errors.append("Exceeds maximum allowed value.")
    return errors


def validate_amount_cents(value) -> list[str]:
    """V2 style: amount as integer (smallest currency unit)."""
    errors = []
    if not isinstance(value, int) or isinstance(value, bool):
        errors.append(
            "Must be an integer representing the smallest currency unit "
            "(e.g. cents for USD, đồng for VND). "
            "Received a float — multiply by 100 before sending."
        )
    elif value <= 0:
        errors.append("Must be greater than 0.")
    elif value > 100_000_000_000:
        errors.append("Exceeds maximum allowed value (100,000,000,000).")
    return errors


def validate_currency(value) -> list[str]:
    if not isinstance(value, str):
        return ["Must be a string."]
    if value.upper() not in SUPPORTED_CURRENCIES:
        return [f"Unsupported currency. Accepted: {sorted(SUPPORTED_CURRENCIES)}."]
    return []


def validate_payment_method(value) -> list[str]:
    if not isinstance(value, str):
        return ["Must be a string."]
    if value not in PAYMENT_METHODS:
        return [f"Unsupported method. Accepted: {sorted(PAYMENT_METHODS)}."]
    return []


def validate_idempotency_key(value) -> list[str]:
    if not isinstance(value, str):
        return ["Must be a string."]
    if len(value) < 8 or len(value) > 128:
        return ["Length must be between 8 and 128 characters."]
    return []


def collect_errors(field_validators: dict) -> list[dict]:
    """
    Run a set of validators and collect all field errors.

    field_validators: {
        "field_name": (value, validator_fn, required=True)
    }
    Returns a list of {"field": ..., "errors": [...]} dicts.
    """
    field_errors = []
    for field, spec in field_validators.items():
        if len(spec) == 3:
            value, fn, required = spec
        else:
            value, fn = spec
            required = True

        if value is None:
            if required:
                field_errors.append({"field": field,
                                     "errors": ["This field is required."]})
        else:
            errs = fn(value)
            if errs:
                field_errors.append({"field": field, "errors": errs})
    return field_errors