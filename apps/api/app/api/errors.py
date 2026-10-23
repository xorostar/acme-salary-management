"""Map domain errors to HTTP responses in one place.

Response body shape (stable for the UI):
    {"detail": "<message>", "errors": [{"field": "...", "message": "..."}]}
`errors` is only present for validation failures.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.domain.errors import (
    AuthenticationError,
    ConflictError,
    DomainError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)

_STATUS: dict[type[DomainError], int] = {
    ValidationError: 422,
    NotFoundError: 404,
    ConflictError: 409,
    PermissionDeniedError: 403,
    AuthenticationError: 401,
}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    def _domain_error(_request: Request, exc: DomainError) -> JSONResponse:
        status = next((s for t, s in _STATUS.items() if isinstance(exc, t)), 400)
        body: dict = {"detail": str(exc)}
        if isinstance(exc, ValidationError):
            body["detail"] = "Validation failed"
            body["errors"] = [{"field": e.field, "message": e.message} for e in exc.errors]
        headers = {"WWW-Authenticate": "Bearer"} if status == 401 else None
        return JSONResponse(status_code=status, content=body, headers=headers)
