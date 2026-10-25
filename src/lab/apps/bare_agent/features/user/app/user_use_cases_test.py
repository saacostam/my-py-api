import pytest

from lab.apps.bare_agent.features.user.app.user_use_cases import UserUseCases
from lab.apps.bare_agent.features.user.domain import User, UserWithPwHash
from lab.apps.bare_agent.features.user.test import mock_user_repository
from lab.apps.bare_agent.shared.adapters.test import (
    mock_id_generator,
    mock_jwt_adapter,
    mock_password_hasher,
)
from lab.shared.errors.domain import DomainError, ErrorType


async def test_signup_returns_created_user_id() -> None:
    jwt_adapter = mock_jwt_adapter()

    id_generator = mock_id_generator()
    id_generator.gen.return_value = "user-1"

    password_hasher = mock_password_hasher()
    password_hasher.hash.return_value = "password-hash"

    created_user = User(
        id="user-1",
        name="John Doe",
    )

    user_repo = mock_user_repository()
    user_repo.get_by_name.return_value = None
    user_repo.create.return_value = created_user

    use_cases = UserUseCases(
        jwt_adapter=jwt_adapter,
        id_generator=id_generator,
        password_hasher=password_hasher,
        user_repo=user_repo,
    )

    result = await use_cases.signup("John Doe", "password")

    assert result == "user-1"

    user_repo.get_by_name.assert_awaited_once_with(name="John Doe")
    id_generator.gen.assert_called_once_with()
    password_hasher.hash.assert_called_once_with(password="password")
    user_repo.create.assert_awaited_once_with(
        UserWithPwHash(
            id="user-1",
            name="John Doe",
            pw_hash="password-hash",
        )
    )


async def test_signup_raises_conflict_when_name_already_exists() -> None:
    jwt_adapter = mock_jwt_adapter()
    id_generator = mock_id_generator()
    password_hasher = mock_password_hasher()

    existing_user = UserWithPwHash(
        id="user-1",
        name="John Doe",
        pw_hash="hashed-password",
    )

    user_repo = mock_user_repository()
    user_repo.get_by_name.return_value = existing_user

    use_cases = UserUseCases(
        jwt_adapter=jwt_adapter,
        id_generator=id_generator,
        password_hasher=password_hasher,
        user_repo=user_repo,
    )

    with pytest.raises(DomainError) as error:
        await use_cases.signup("John Doe", "password")

    assert error.value.type == ErrorType.CONFLICT
    assert error.value.user_msg == "Name already in use"
    assert error.value.fields == [{"field": "name", "message": "Duplicated"}]

    user_repo.get_by_name.assert_awaited_once_with(name="John Doe")
    password_hasher.hash.assert_not_called()
    user_repo.create.assert_not_awaited()


async def test_login_returns_jwt_token() -> None:
    jwt_adapter = mock_jwt_adapter()
    jwt_adapter.get_token.return_value = "mock-jwt-token"

    id_generator = mock_id_generator()

    password_hasher = mock_password_hasher()
    password_hasher.verify.return_value = True

    existing_user = UserWithPwHash(
        id="user-1",
        name="John Doe",
        pw_hash="hashed-password",
    )

    user_repo = mock_user_repository()
    user_repo.get_by_name.return_value = existing_user

    use_cases = UserUseCases(
        jwt_adapter=jwt_adapter,
        id_generator=id_generator,
        password_hasher=password_hasher,
        user_repo=user_repo,
    )

    token = await use_cases.login("John Doe", "password123")

    assert token == "mock-jwt-token"
    user_repo.get_by_name.assert_awaited_once_with(name="John Doe")
    password_hasher.verify.assert_called_once_with(
        plain_password="password123", hashed_password="hashed-password"
    )
    jwt_adapter.get_token.assert_called_once_with("user-1")


async def test_login_raises_bad_request_when_user_not_found() -> None:
    jwt_adapter = mock_jwt_adapter()
    id_generator = mock_id_generator()
    password_hasher = mock_password_hasher()

    user_repo = mock_user_repository()
    user_repo.get_by_name.return_value = None

    use_cases = UserUseCases(
        jwt_adapter=jwt_adapter,
        id_generator=id_generator,
        password_hasher=password_hasher,
        user_repo=user_repo,
    )

    with pytest.raises(DomainError) as error:
        await use_cases.login("Unknown User", "password123")

    assert error.value.type == ErrorType.BAD_REQUEST
    assert error.value.user_msg == "Invalid credentials"
    assert error.value.msg == "Authentication failed for user 'Unknown User'"

    user_repo.get_by_name.assert_awaited_once_with(name="Unknown User")
    password_hasher.verify.assert_not_called()
    jwt_adapter.get_token.assert_not_called()


async def test_login_raises_bad_request_when_password_is_invalid() -> None:
    jwt_adapter = mock_jwt_adapter()
    id_generator = mock_id_generator()

    password_hasher = mock_password_hasher()
    password_hasher.verify.return_value = False

    existing_user = UserWithPwHash(
        id="user-1",
        name="John Doe",
        pw_hash="hashed-password",
    )

    user_repo = mock_user_repository()
    user_repo.get_by_name.return_value = existing_user

    use_cases = UserUseCases(
        jwt_adapter=jwt_adapter,
        id_generator=id_generator,
        password_hasher=password_hasher,
        user_repo=user_repo,
    )

    with pytest.raises(DomainError) as error:
        await use_cases.login("John Doe", "wrong-password")

    assert error.value.type == ErrorType.BAD_REQUEST
    assert error.value.user_msg == "Invalid credentials"
    assert error.value.msg == "Authentication failed for user 'John Doe'"

    user_repo.get_by_name.assert_awaited_once_with(name="John Doe")
    password_hasher.verify.assert_called_once_with(
        plain_password="wrong-password", hashed_password="hashed-password"
    )
    jwt_adapter.get_token.assert_not_called()


async def test_get_by_id_returns_user() -> None:
    jwt_adapter = mock_jwt_adapter()
    id_generator = mock_id_generator()
    password_hasher = mock_password_hasher()

    user = User(
        id="user-1",
        name="John Doe",
    )

    user_repo = mock_user_repository()
    user_repo.get_by_id.return_value = user

    use_cases = UserUseCases(
        jwt_adapter=jwt_adapter,
        id_generator=id_generator,
        password_hasher=password_hasher,
        user_repo=user_repo,
    )

    result = await use_cases.get_by_id("user-1")

    assert result == user
    user_repo.get_by_id.assert_awaited_once_with(user_id="user-1")


async def test_get_by_id_raises_not_found() -> None:
    jwt_adapter = mock_jwt_adapter()
    id_generator = mock_id_generator()
    password_hasher = mock_password_hasher()

    user_repo = mock_user_repository()
    user_repo.get_by_id.return_value = None

    use_cases = UserUseCases(
        jwt_adapter=jwt_adapter,
        id_generator=id_generator,
        password_hasher=password_hasher,
        user_repo=user_repo,
    )

    with pytest.raises(DomainError) as error:
        await use_cases.get_by_id("user-1")

    assert error.value.type == ErrorType.NOT_FOUND
    assert error.value.user_msg == "User not found."
    assert error.value.msg == "User with id 'user-1' was not found"

    user_repo.get_by_id.assert_awaited_once_with(user_id="user-1")
