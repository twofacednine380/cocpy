class COCAPIError(Exception):
    """Base error for Clash of Clans API failures."""

class AuthError(COCAPIError):
    """401/403 authentication or authorization error."""

class NotFoundError(COCAPIError):
    """404 resource not found."""

class RateLimitError(COCAPIError):
    """429 rate limit exceeded."""