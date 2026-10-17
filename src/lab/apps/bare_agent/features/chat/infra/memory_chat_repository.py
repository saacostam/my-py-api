from lab.apps.bare_agent.features.chat.domain import Chat, LeanChat


class MemoryChatRepository:
    def __init__(self) -> None:
        self._chats: list[Chat] = []

    async def create(self, chat: Chat) -> Chat:
        self._chats.append(chat)
        return chat

    async def get_by_id(self, id: str) -> Chat | None:
        for chat in self._chats:
            if chat.id == id:
                return chat

        return None

    async def get_all_by_user_id(self, user_id: str) -> list[LeanChat]:
        chats: list[LeanChat] = []

        for chat in self._chats:
            if chat.user_id == user_id:
                chats.append(chat)

        return chats

    async def remove(self, id: str) -> str:
        self._chats = [chat for chat in self._chats if chat.id != id]
        return id

    async def update(self, chat_id: str, chat: Chat) -> Chat:
        self._chats = [
            chat if current.id == chat_id else current for current in self._chats
        ]
        return chat
