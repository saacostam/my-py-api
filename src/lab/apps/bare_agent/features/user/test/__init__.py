from unittest.mock import Mock

from lab.apps.todo.features.user.domain import UserRepository


def mock_user_repository():
    return Mock(spec=UserRepository)
