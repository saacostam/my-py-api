import jwt

from lab.apps.todo.shared.adapters.domain import TokenPayload

SECRET = "REPLACE_ME"
ALGORITHM = "HS256"


class PyJwtAdapter:
    def get_token(self, user_id: str) -> str:
        return jwt.encode({"user_id": user_id}, SECRET, algorithm=ALGORITHM)

    def validate_token(self, token: str) -> TokenPayload | None:
        try:
            payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])

            user_id = payload.get("user_id")
            if not user_id:
                return None

            return TokenPayload(user_id=user_id)

        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return None
