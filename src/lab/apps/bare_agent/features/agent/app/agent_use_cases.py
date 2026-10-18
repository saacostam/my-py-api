from dataclasses import dataclass

from lab.apps.bare_agent.features.agent.domain import (
    ChainOfThought,
    ChainOfThoughtRepository,
)
from lab.apps.bare_agent.features.chat.domain import (
    Chat,
    ChatRepository,
    ChunkBufferRepository,
    LeanChat,
    Turn,
    TurnStatus,
    TurnType,
)
from lab.apps.bare_agent.shared.adapters.domain import (
    IdGenerator,
    Queue,
    QueueEntry,
)
from lab.shared.errors.domain import DomainError, ErrorType

from .types import ChatDetails, ErrorTurn, ProcessingTurn, SuccessTurn


@dataclass
class ChatIdentifier:
    chat_id: str


USER_ID = "public"


class AgentUseCases:
    def __init__(
        self,
        chat_repo: ChatRepository,
        chunk_buffer_repo: ChunkBufferRepository,
        cot_repo: ChainOfThoughtRepository,
        id_generator: IdGenerator,
        queue: Queue,
    ):
        self._chat_repo = chat_repo
        self._chunk_buffer_repo = chunk_buffer_repo
        self._cot_repo = cot_repo
        self._id_generator = id_generator
        self._queue = queue

    async def create(self, message: str) -> ChatIdentifier:
        # Create Chat
        chat_id = self._id_generator.gen()
        user_turn_id = self._id_generator.gen()
        response_turn_id = self._id_generator.gen()

        chat_to_be_created: Chat = Chat(
            id=chat_id,
            user_id=USER_ID,
            turns=[
                Turn(
                    id=user_turn_id,
                    type=TurnType.USER,
                    content=message,
                    status=TurnStatus.SUCCESS,
                ),
                Turn(
                    id=response_turn_id,
                    type=TurnType.ASSISTANT,
                    content="",
                    status=TurnStatus.PROCESSING,
                ),
            ],
        )

        chat = await self._chat_repo.create(chat=chat_to_be_created)

        chain_identifier = await self._start_chain_of_though(
            chat_id=chat.id,
            message=message,
            turn_id=response_turn_id,
        )

        return chain_identifier

    async def get_all_chats(self) -> list[LeanChat]:
        chats = await self._chat_repo.get_all_by_user_id(user_id=USER_ID)

        return chats

    async def get_by_id(self, chat_id: str) -> ChatDetails:
        chat = await self._get_owned_chat_by_id(chat_id=chat_id)

        processing_turn_ids = [
            turn.id for turn in chat.turns if turn.status == TurnStatus.PROCESSING
        ]

        chunks_by_turn_id = (
            await self._chunk_buffer_repo.get_all_by_turn_ids(
                turn_ids=processing_turn_ids,
            )
            if processing_turn_ids
            else {}
        )

        turns: list[SuccessTurn | ErrorTurn | ProcessingTurn] = []

        for turn in chat.turns:
            if turn.status == TurnStatus.SUCCESS:
                turns.append(
                    SuccessTurn(
                        id=turn.id,
                        type=turn.type,
                        status=TurnStatus.SUCCESS,
                        content=turn.content,
                    )
                )
            elif turn.status == TurnStatus.ERROR:
                turns.append(
                    ErrorTurn(
                        id=turn.id,
                        type=turn.type,
                        status=TurnStatus.ERROR,
                        content=turn.content,
                    )
                )
            else:
                turns.append(
                    ProcessingTurn(
                        id=turn.id,
                        type=turn.type,
                        status=TurnStatus.PROCESSING,
                        chunks=chunks_by_turn_id.get(turn.id, []),
                    )
                )

        return ChatDetails(
            id=chat.id,
            user_id=chat.user_id,
            turns=turns,
        )

    async def resume(self, chat_id: str, message: str) -> ChatIdentifier:
        chat = await self._get_owned_chat_by_id(chat_id=chat_id)

        chat.turns.append(
            Turn(
                id=self._id_generator.gen(),
                type=TurnType.USER,
                content=message,
                status=TurnStatus.SUCCESS,
            ),
        )

        response_turn_id = self._id_generator.gen()
        chat.turns.append(
            Turn(
                id=response_turn_id,
                type=TurnType.ASSISTANT,
                content="",
                status=TurnStatus.PROCESSING,
            )
        )

        updated_chat = await self._chat_repo.update(chat_id=chat.id, chat=chat)

        chain_identifier = await self._start_chain_of_though(
            chat_id=updated_chat.id,
            message=message,
            turn_id=response_turn_id,
        )

        return chain_identifier

    async def _get_owned_chat_by_id(self, chat_id: str) -> Chat:
        chat = await self._chat_repo.get_by_id(id=chat_id)

        if chat is None:
            raise DomainError(
                msg="Chat was not found",
                type=ErrorType.NOT_FOUND,
                user_msg=f"Chat with id {chat_id} was not found",
            )

        return chat

    async def _start_chain_of_though(self, chat_id: str, message: str, turn_id: str):
        # Create CoT
        chain_of_though_to_be_created: ChainOfThought = ChainOfThought(
            id=self._id_generator.gen(),
            chat_id=chat_id,
            objective=f"Answer this message from the user: ${message}",
            thoughts=[],
        )

        cot = await self._cot_repo.create(chain_of_though_to_be_created)

        # Schedule Though Loop
        await self._queue.add(
            QueueEntry(
                id=self._id_generator.gen(),
                chat_id=chat_id,
                cot_id=cot.id,
                turn_id=turn_id,
                type="decision",
            )
        )

        return ChatIdentifier(
            chat_id=chat_id,
        )
