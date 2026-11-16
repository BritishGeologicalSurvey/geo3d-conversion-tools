"""Helpers for working with types.
© UKRI (British Geological Survey) and the Polish Geological Institute 2026.
"""


def require_not_none[T](value: T | None, error_msg: str = "Required value is missing (received None)") -> T:
    """Strips 'None' from any optional type, or raises a ValueError."""
    if value is None:
        raise ValueError(error_msg)
    return value
