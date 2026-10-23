"""Typed errors raised by domain and service code.

The API layer maps these to HTTP responses in one place, so services never
import HTTPException.
"""

from dataclasses import dataclass


class DomainError(Exception):
    """Base class for all expected business errors."""


@dataclass(frozen=True)
class FieldError:
    field: str
    message: str


class ValidationError(DomainError):
    """One or more field-level problems. Collects everything so the UI can
    show all errors at once instead of one per round trip."""

    def __init__(self, errors: list[FieldError]):
        self.errors = errors
        super().__init__("; ".join(f"{e.field}: {e.message}" for e in errors))

    @classmethod
    def single(cls, field: str, message: str) -> "ValidationError":
        return cls([FieldError(field, message)])


class NotFoundError(DomainError):
    pass


class ConflictError(DomainError):
    """Duplicate key or stale version."""


class PermissionDeniedError(DomainError):
    pass


class AuthenticationError(DomainError):
    pass
