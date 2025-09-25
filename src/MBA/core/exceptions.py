"""
Custom exceptions for the MBA ingestion system.

This module defines a hierarchy of domain-specific exceptions to provide
consistent error handling across ingestion components. Each exception
inherits from `MBAIngestionError`, which allows structured error reporting
with optional details.
"""
from typing import Optional, Any


class MBAIngestionError(Exception):
    """Base exception for all HMA ingestion errors."""
    
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        """Initialize exception with message and optional details."""
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigError(MBAIngestionError):
    """Raised when configuration is invalid or missing."""
    pass


class UploadError(MBAIngestionError):
    """Raised when S3 upload fails."""
    pass


class FileDiscoveryError(MBAIngestionError):
    """Raised when file discovery or processing fails."""
    pass


class QueueError(MBAIngestionError):
    """Raised when queue operations fail."""
    pass