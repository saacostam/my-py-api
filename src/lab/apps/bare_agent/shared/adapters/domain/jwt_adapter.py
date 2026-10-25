from dataclasses import dataclass
from typing import Protocol


@dataclass
class TokenPayload:
    user_id: str


class JwtAdapter(Protocol):
    def get_token(self, user_id: str) -> str: ...
    def validate_token(self, token: str) -> TokenPayload | None: ...
