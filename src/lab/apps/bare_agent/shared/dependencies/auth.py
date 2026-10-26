from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from lab.apps.bare_agent.features.auth.app import AuthUseCases
from lab.apps.bare_agent.shared.adapters.domain import TokenPayload

security = HTTPBearer()


class AuthDependency:
    """Callable class acting as a FastAPI dependency using your JwtAdapter protocol."""

    def __init__(self, auth_use_cases: AuthUseCases):
        self.auth_use_cases = auth_use_cases

    def __call__(
        self, credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> TokenPayload:
        return self.auth_use_cases.validate(credentials.credentials)
