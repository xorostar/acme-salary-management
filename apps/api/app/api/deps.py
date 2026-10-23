"""FastAPI dependencies: session, clock, settings, current user, role guard."""

from collections.abc import Callable, Iterator
from datetime import date
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import Settings
from app.db import session_scope
from app.domain.errors import AuthenticationError, PermissionDeniedError
from app.services.auth import AuthService, CurrentUser

Clock = Callable[[], date]

_bearer = HTTPBearer(auto_error=False)


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_session(request: Request) -> Iterator[Session]:
    yield from session_scope(request.app.state.session_factory)


def get_clock(request: Request) -> Clock:
    return request.app.state.clock


def get_today(clock: Annotated[Clock, Depends(get_clock)]) -> date:
    return clock()


SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings_dep)]
TodayDep = Annotated[date, Depends(get_today)]


def get_auth_service(session: SessionDep, settings: SettingsDep) -> AuthService:
    return AuthService(
        session, jwt_secret=settings.jwt_secret, jwt_expiry_hours=settings.jwt_expiry_hours
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    auth: AuthServiceDep,
) -> CurrentUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError("Missing bearer token")
    return auth.authenticate(credentials.credentials)


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


def require_role(*roles: str) -> Callable[[CurrentUser], CurrentUser]:
    """Dependency factory: `Depends(require_role("hr_admin"))`."""

    def _check(user: CurrentUserDep) -> CurrentUser:
        if user.role not in roles:
            raise PermissionDeniedError(f"Requires one of roles: {', '.join(roles)}")
        return user

    return _check
