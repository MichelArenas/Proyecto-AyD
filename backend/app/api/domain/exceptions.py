"""Custom exceptions for the application domain."""

from typing import List, Optional


class DomainException(Exception):
    """Base exception for domain errors with optional HTTP semantics."""

    def __init__(
        self,
        message: str,
        *,
        errors: Optional[List] = None,
        status_code: int = 400,
    ):
        super().__init__(message)
        self.message = message
        self.errors = errors or []
        self.status_code = status_code


class ValidationError(DomainException):
    """Validation failed"""

    def __init__(self, message: str, errors: Optional[List] = None):
        super().__init__(message, errors=errors, status_code=422)
