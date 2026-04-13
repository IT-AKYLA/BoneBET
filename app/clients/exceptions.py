"""Custom exceptions for API clients."""

class CS2APIError(Exception):
    """Base exception for CS2 Analytics API errors."""

class CS2APIConnectionError(CS2APIError):
    """Connection error (timeout, network)."""

class CS2APIResponseError(CS2APIError):
    """Invalid response (4xx, 5xx)."""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"HTTP {status_code}: {message}")

class CS2APIParsingError(CS2APIError):
    """Failed to parse response JSON."""

class PlayerNotFoundError(CS2APIError):
    """Player not found in API."""

class TeamNotFoundError(CS2APIError):
    """Team not found in API."""

class DataLoadingError(CS2APIError):
    """Data is still loading in background."""
    def __init__(self, entity: str, identifier: str):
        self.entity = entity
        self.identifier = identifier
        super().__init__(f"{entity} '{identifier}' data is loading, retry later")