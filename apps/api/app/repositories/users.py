from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User


class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, user_id: int) -> User | None:
        return self.session.get(User, user_id)

    def find_by_email(self, email: str) -> User | None:
        """Login is by email alone. Emails are unique per organization (ADR 004);
        with one organization today this is unambiguous. A second organization
        would add an organization slug to the login form."""
        stmt = select(User).where(User.email == email.strip().lower()).order_by(User.id)
        return self.session.scalars(stmt).first()

    def add(self, user: User) -> User:
        self.session.add(user)
        self.session.flush()
        return user
