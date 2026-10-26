"""Password hashing and JWT helpers. Thin wrappers so the rest of the app
never imports bcrypt or jwt directly."""

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.domain.errors import AuthenticationError

ALGORITHM = "HS256"


BCRYPT_ROUNDS = 12


def hash_password(password: str, *, rounds: int = BCRYPT_ROUNDS) -> str:
    """Tests pass a low `rounds` for speed; verification reads the cost from the hash."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=rounds)).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except ValueError:
        return False


def create_token(
    *,
    secret: str,
    user_id: int,
    organization_id: int,
    role: str,
    expires_in: timedelta,
    now: datetime | None = None,
) -> str:
    issued = now or datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "org": organization_id,
        "role": role,
        "iat": issued,
        "exp": issued + expires_in,
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def decode_token(token: str, *, secret: str) -> dict:
    try:
        return jwt.decode(token, secret, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired") from None
    except jwt.InvalidTokenError:
        raise AuthenticationError("Invalid token") from None
