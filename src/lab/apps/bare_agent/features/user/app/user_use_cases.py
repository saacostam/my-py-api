from lab.apps.bare_agent.features.user.domain import (
    User,
    UserRepository,
    UserWithPwHash,
)
from lab.apps.bare_agent.shared.adapters.domain import (
    IdGenerator,
    JwtAdapter,
    PasswordHasher,
)
from lab.shared.errors.domain import DomainError, ErrorType


class UserUseCases:
    def __init__(
        self,
        jwt_adapter: JwtAdapter,
        id_generator: IdGenerator,
        password_hasher: PasswordHasher,
        user_repo: UserRepository,
    ) -> None:
        self.jwt_adapter = jwt_adapter
        self.id_generator = id_generator
        self.password_hasher = password_hasher
        self.user_repo = user_repo

    async def get_by_id(self, id: str) -> User:
        user = await self.user_repo.get_by_id(user_id=id)

        if user is None:
            raise DomainError(
                msg=f"User with id '{id}' was not found",
                type=ErrorType.NOT_FOUND,
                user_msg="User not found.",
            )

        return user

    async def login(self, name: str, password: str) -> str:
        user = await self.user_repo.get_by_name(name=name)

        discrete_error = DomainError(
            msg=f"Authentication failed for user '{name}'",
            type=ErrorType.BAD_REQUEST,
            user_msg="Invalid credentials",
        )

        if user is None:
            raise discrete_error

        password_is_valid = self.password_hasher.verify(
            plain_password=password, hashed_password=user.pw_hash
        )

        if not password_is_valid:
            raise discrete_error

        token = self.jwt_adapter.get_token(user.id)

        return token

    async def signup(self, name: str, password: str) -> str:
        existing_user = await self.user_repo.get_by_name(name=name)

        if existing_user is not None:
            raise DomainError(
                msg=f"Signup failed: username '{name}' is already taken",
                type=ErrorType.CONFLICT,
                user_msg="Name already in use",
                fields=[{"field": "name", "message": "Duplicated"}],
            )

        pw_hash = self.password_hasher.hash(password=password)

        user = UserWithPwHash(
            id=self.id_generator.gen(),
            name=name,
            pw_hash=pw_hash,
        )

        created_user = await self.user_repo.create(user)

        return created_user.id
