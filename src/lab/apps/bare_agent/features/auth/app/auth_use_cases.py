from lab.apps.bare_agent.shared.adapters.domain import (
    JwtAdapter,
    TokenPayload,
)
from lab.shared.errors.domain import DomainError, ErrorType


class AuthUseCases:
    def __init__(
        self,
        jwt: JwtAdapter,
    ):
        self._jwt = jwt

    def validate(self, token: str) -> TokenPayload:
        payload = self._jwt.validate_token(token)

        if not payload:
            raise DomainError(
                msg="Token validation failed or expired",
                type=ErrorType.UNAUTHORIZED,
                user_msg="Your session has expired or is invalid. Please log in again.",
            )

        return payload
