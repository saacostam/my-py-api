from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from lab.apps.bare_agent.shared.adapters.domain import JwtAdapter, TokenPayload
from lab.shared.errors.domain import DomainError, ErrorType

security = HTTPBearer()


class AuthDependency:
    """Callable class acting as a FastAPI dependency using your JwtAdapter protocol."""

    def __init__(self, jwt_adapter: JwtAdapter):
        self.jwt_adapter = jwt_adapter

    def __call__(
        self, credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> TokenPayload:
        payload = self.jwt_adapter.validate_token(credentials.credentials)

        if not payload:
            raise DomainError(
                msg="Token validation failed or expired",
                type=ErrorType.UNAUTHORIZED,
                user_msg="Your session has expired or is invalid. Please log in again.",
            )

        return payload
