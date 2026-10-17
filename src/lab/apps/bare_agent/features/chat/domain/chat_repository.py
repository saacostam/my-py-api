from dataclasses import dataclass
from typing import Protocol

from .chat import Chat, LeanChat, TurnStatus


@dataclass
class UpdateTurnPayload:
    content: str | None = None
    status: TurnStatus | None = None


class ChatRepository(Protocol):
    async def create(self, chat: Chat) -> Chat: ...
    async def get_by_id(self, id: str) -> Chat | None: ...
    async def get_all_by_user_id(self, user_id: str) -> list[LeanChat]: ...
    async def remove(self, id: str) -> str: ...
    async def update(self, chat_id: str, chat: Chat) -> Chat: ...
    async def update_turn(
        self, id: str, turn_id: str, turn: UpdateTurnPayload
    ) -> None: ...
