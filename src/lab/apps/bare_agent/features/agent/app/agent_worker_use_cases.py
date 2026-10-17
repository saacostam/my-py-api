from typing import Literal

from pydantic import BaseModel

from lab.apps.bare_agent.features.agent.domain import (
    ChainOfThoughtRepository,
)
from lab.apps.bare_agent.features.chat.domain import (
    ChatRepository,
    Chunk,
    ChunkBufferRepository,
    Turn,
    TurnStatus,
    TurnType,
    UpdateTurnPayload,
)
from lab.apps.bare_agent.shared.adapters.domain import (
    EventCompleted,
    EventCreated,
    EventEmitter,
    EventError,
    EventMessage,
    IdGenerator,
    LLMProvider,
    Logger,
    Message,
    MessageRole,
    Queue,
    QueueEntry,
)
from lab.shared.errors.domain import DomainError, ErrorType


class AgentDecision(BaseModel):
    decision: Literal["response", "tools"]


class AgentResponse(BaseModel):
    content: str


class AgentWorkerUseCases:
    def __init__(
        self,
        chat_repo: ChatRepository,
        chunk_buffer_repo: ChunkBufferRepository,
        cot_repo: ChainOfThoughtRepository,
        id_generator: IdGenerator,
        llm: LLMProvider,
        logger: Logger,
        queue: Queue,
        user_event_emitter: EventEmitter,
    ):
        self._chat_repo = chat_repo
        self._chunk_buffer_repo = chunk_buffer_repo
        self._cot_repo = cot_repo
        self._id_generator = id_generator
        self._llm = llm
        self._logger = logger
        self._queue = queue
        self._user_event_emitter = user_event_emitter

    async def decision(
        self,
        chat_id: str,
        cot_id: str,
    ) -> None:
        chat = await self._chat_repo.get_by_id(id=chat_id)

        if chat is None:
            raise DomainError(
                msg=f"AgentWorkerUseCases.decision: Chat {chat_id} not found",
                type=ErrorType.NOT_FOUND,
                user_msg="Failed to process missing chat",
            )

        messages = [
            Message(
                role=MessageRole.SYSTEM,
                content=(
                    "Decide whether the user's request can be answered "
                    "directly or requires tools. Choose 'response' for a "
                    "direct answer and 'tools' when tools are necessary."
                ),
            ),
            *[
                Message(
                    role=(
                        MessageRole.USER
                        if turn.type == TurnType.USER
                        else MessageRole.ASSISTANT
                    ),
                    content=turn.content,
                )
                for turn in chat.turns
            ],
        ]

        result = await self._llm.generate(
            messages=messages,
            output_schema=AgentDecision,
        )
        decision = result.decision

        self._logger.info(f"Worker.decision.{chat_id}.{cot_id} Decision was {decision}")

        if decision == "tools":
            # Tool execution is not implemented yet.
            raise NotImplementedError("Tool execution is not implemented")

        else:
            await self._queue.add(
                QueueEntry(
                    id=self._id_generator.gen(),
                    chat_id=chat_id,
                    cot_id=cot_id,
                    type="response",
                )
            )

    async def response(
        self,
        chat_id: str,
        cot_id: str,
    ) -> None:
        chat = await self._chat_repo.get_by_id(id=chat_id)

        if chat is None:
            raise DomainError(
                msg=f"AgentWorkerUseCases.response: Chat {chat_id} not found",
                type=ErrorType.NOT_FOUND,
                user_msg="Failed to respond to missing chat",
            )

        messages = [
            Message(
                role=MessageRole.SYSTEM,
                content="Answer the user's latest message helpfully and accurately.",
            ),
            *[
                Message(
                    role=(
                        MessageRole.USER
                        if turn.type == TurnType.USER
                        else MessageRole.ASSISTANT
                    ),
                    content=turn.content,
                )
                for turn in chat.turns
            ],
        ]

        turn_id = self._id_generator.gen()
        chat.turns.append(
            Turn(
                id=turn_id,
                type=TurnType.ASSISTANT,
                content="",
                status=TurnStatus.PROCESSING,
            )
        )

        await self._chat_repo.update(chat_id=chat_id, chat=chat)

        full_response: list[str] = []

        async def on_created() -> None:
            await self._user_event_emitter.send(
                id=chat.user_id,
                event=EventCreated(turn_id=turn_id),
            )

        async def on_message(chunk: str, index: int) -> None:
            full_response.append(chunk)

            # Persist the chunk before notifying the client.
            await self._chunk_buffer_repo.create(
                Chunk(
                    index=index,
                    turn_id=turn_id,
                    content=chunk,
                )
            )

            await self._user_event_emitter.send(
                id=chat.user_id,
                event=EventMessage(content=chunk, turn_id=turn_id),
            )

        async def on_completed() -> None:
            await self._chat_repo.update_turn(
                id=chat.id,
                turn_id=turn_id,
                turn=UpdateTurnPayload(
                    status=TurnStatus.SUCCESS,
                    content="".join(full_response),
                ),
            )

            await self._user_event_emitter.send(
                id=chat.user_id,
                event=EventCompleted(turn_id=turn_id),
            )

        async def on_error(error: str) -> None:
            await self._chat_repo.update_turn(
                id=chat.id,
                turn_id=turn_id,
                turn=UpdateTurnPayload(
                    status=TurnStatus.ERROR, content="".join(full_response)
                ),
            )

            await self._user_event_emitter.send(
                id=chat.user_id,
                event=EventError(message=error, turn_id=turn_id),
            )

        await self._llm.stream(
            messages=messages,
            onCreated=on_created,
            onMessage=on_message,
            onCompleted=on_completed,
            onError=on_error,
        )
