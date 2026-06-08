import httpx


class OptionTickerNeverActiveError(Exception):
    """Raised when a snapshot has no usable market activity timestamp."""

    pass


def is_retryable_db_error(error: Exception) -> bool:
    """Return True when the error looks like a transient database connectivity fault."""
    message = str(error)
    type_name = type(error).__name__

    if type_name == "ClientNotConnectedError":
        return True
    if isinstance(error, (httpx.ReadError, httpx.RemoteProtocolError)):
        return True
    if "P1001" in message:
        return True
    if "Can't reach database server" in message:
        return True

    return False
