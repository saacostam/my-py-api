from unittest.mock import Mock
from uuid import uuid4

from lab.apps.todo.features.user.domain import (
    User,
    UserRepository,
    UserStatus,
)


def mock_user_repository():
    return Mock(spec=UserRepository)


def seed_user(
    id: str | None,
    name: str | None,
    status: UserStatus | None,
) -> User:
    return User(
        id=id if id else str(uuid4()),
        name=name if name else str(uuid4()),
        status=status if status else UserStatus.ACTIVE,
    )
