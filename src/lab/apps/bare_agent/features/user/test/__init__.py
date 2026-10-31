from unittest.mock import Mock
from uuid import uuid4

from lab.apps.todo.features.user.domain import (
    UserRepository,
    UserStatus,
    UserWithPwHash,
)


def mock_user_repository():
    return Mock(spec=UserRepository)


def seed_user(
    id: str | None = None,
    name: str | None = None,
    status: UserStatus | None = None,
    pw_hash: str | None = None,
) -> UserWithPwHash:
    return UserWithPwHash(
        id=id if id else str(uuid4()),
        name=name if name else str(uuid4()),
        status=status if status else UserStatus.ACTIVE,
        pw_hash=pw_hash if pw_hash else str(uuid4()),
    )
