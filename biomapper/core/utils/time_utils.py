from datetime import datetime, timezone


def get_current_utc_time() -> datetime:
    """Return the current time in UTC timezone."""
    return datetime.now(timezone.utc)
