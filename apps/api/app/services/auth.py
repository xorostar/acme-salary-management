from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.orm import Session

from app.domain.errors import AuthenticationError
from app.domain.reference import ROLES
from app.models import User
from app.repositories.users import UserRepository
from app.security import create_token, decode_token, verify_password


@dataclass(frozen=True)
class CurrentUser:
    id: int
    organization_id: int
    email: str
    full_name: str
    role: str


@dataclass(frozen=True)
class LoginResult:
    token: str
    user: CurrentUser


def _to_current_user(user: User) -> CurrentUser:
    return CurrentUser(
        id=user.id,
        organization_id=user.organization_id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
    )


class AuthService:
    def __init__(self, session: Session, *, jwt_secret: str, jwt_expiry_hours: int):
        self.users = UserRepository(session)
        self.jwt_secret = jwt_secret
        self.jwt_expiry = timedelta(hours=jwt_expiry_hours)

    def login(self, email: str, password: str) -> LoginResult:
        user = self.users.find_by_email(email)
        # Verify against a dummy hash when the user is missing so response time
        # does not reveal whether the email exists.
        if user is None or not verify_password(password, user.password_hash):
            if user is None:
                verify_password(password, _DUMMY_HASH)
            raise AuthenticationError("Invalid email or password")
        if user.role not in ROLES:
            raise AuthenticationError("User has no valid role")
        token = create_token(
            secret=self.jwt_secret,
            user_id=user.id,
            organization_id=user.organization_id,
            role=user.role,
            expires_in=self.jwt_expiry,
        )
        return LoginResult(token=token, user=_to_current_user(user))

    def authenticate(self, token: str) -> CurrentUser:
        """Resolve a bearer token to the user it names. The user is re-read so a
        role change takes effect without waiting for token expiry."""
        payload = decode_token(token, secret=self.jwt_secret)
        try:
            user_id = int(payload["sub"])
        except (KeyError, ValueError):
            raise AuthenticationError("Invalid token") from None
        user = self.users.get(user_id)
        if user is None:
            raise AuthenticationError("User no longer exists")
        return _to_current_user(user)


# bcrypt hash of an unguessable string; only used to equalize timing on unknown emails.
_DUMMY_HASH = "$2b$12$pKTCYUL0N7GmJGuylO8M1OZFX9ozTfipTFhGaK3hs8j84fy4Fn9Am"
