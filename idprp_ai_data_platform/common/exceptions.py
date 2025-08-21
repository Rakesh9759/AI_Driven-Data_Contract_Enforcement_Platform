"""Shared exception types for platform modules."""


class PlatformError(Exception):
    """Base platform exception for recoverable application failures."""


class ConfigurationError(PlatformError):
    """Raised when configuration files are missing or malformed."""
