from unittest.mock import call

import pytest

from lab.apps.bare_agent.features.agent.app import (
    AgentWorkerUseCases,
)
from lab.apps.bare_agent.features.agent.test import (
    mock_chain_of_thought_repository,
)
from lab.apps.bare_agent.features.chat.domain import (
    Chat,
    Chunk,
    Turn,
    TurnStatus,
    TurnType,
)
from lab.apps.bare_agent.features.chat.test import (
    mock_chat_repository,
    mock_chunk_buffer_repository,
)
from lab.apps.bare_agent.shared.adapters.domain import (
    EventCompleted,
    EventCreated,
    EventError,
    EventMessage,
    Message,
    MessageRole,
)
from lab.apps.bare_agent.shared.adapters.test import (
    mock_event_emitter,
    mock_id_generator,
    mock_llm_provider,
    mock_logger,
    mock_queue,
)
from lab.shared.errors.domain import DomainError, ErrorType


def make_use_cases(
    *,
    chat_repo,
    chunk_buffer_repo,
    id_generator,
    llm,
    logger=None,
    queue=None,
    event_emitter=None,
) -> AgentWorkerUseCases:
    return AgentWorkerUseCases(
        chat_repo=chat_repo,
        chunk_buffer_repo=chunk_buffer_repo,
        cot_repo=mock_chain_of_thought_repository(),
        id_generator=id_generator,
        llm=llm,
        logger=logger or mock_logger(),
        queue=queue or mock_queue(),
        user_event_emitter=event_emitter or mock_event_emitter(),
    )


async def test_response_success() -> None:
    id_generator = mock_id_generator()

    existing_chat = Chat(
        id="chat-id-123",
        user_id="public",
        turns=[
            Turn(
                id="user-turn-id-123",
                type=TurnType.USER,
                content="Hello",
                status=TurnStatus.SUCCESS,
            ),
            Turn(
                id="turn-id",
                type=TurnType.ASSISTANT,
                content="",
                status=TurnStatus.PROCESSING,
            ),
        ],
    )
    chat_repo = mock_chat_repository()
    chat_repo.get_by_id.return_value = existing_chat
    chat_repo.update.return_value = existing_chat

    chunk_buffer_repo = mock_chunk_buffer_repository()
    llm = mock_llm_provider()
    event_emitter = mock_event_emitter()

    async def send_side_effect(*, id, event) -> None:
        if isinstance(event, EventCompleted):
            # The final turn state must be persisted before completion is emitted.
            chat_repo.update_turn.assert_awaited_once()
            update_payload = chat_repo.update_turn.await_args.kwargs["turn"]
            assert update_payload.content == "Hello world"
            assert update_payload.status == TurnStatus.SUCCESS

    event_emitter.send.side_effect = send_side_effect

    async def stream_side_effect(
        *, messages, onCreated, onMessage, onCompleted, onError
    ) -> None:
        assert messages == [
            Message(
                role=MessageRole.SYSTEM,
                content="Answer the user's latest message helpfully and accurately.",
            ),
            Message(role=MessageRole.USER, content="Hello"),
        ]
        await onCreated()
        await onMessage("Hello", 0)
        await onMessage(" world", 1)
        await onCompleted()

    llm.stream.side_effect = stream_side_effect

    use_cases = make_use_cases(
        chat_repo=chat_repo,
        chunk_buffer_repo=chunk_buffer_repo,
        id_generator=id_generator,
        llm=llm,
        event_emitter=event_emitter,
    )

    await use_cases.response(
        chat_id="chat-id-123", cot_id="cot-id-123", turn_id="turn-id"
    )

    chat_repo.get_by_id.assert_awaited_once_with(id="chat-id-123")

    chat_repo.update_turn.assert_awaited_once()
    update_call = chat_repo.update_turn.await_args
    assert update_call.kwargs["id"] == "chat-id-123"
    assert update_call.kwargs["turn_id"] == "turn-id"
    assert update_call.kwargs["turn"].content == "Hello world"
    assert update_call.kwargs["turn"].status == TurnStatus.SUCCESS

    assert chunk_buffer_repo.create.await_args_list == [
        call(Chunk(index=0, turn_id="turn-id", content="Hello")),
        call(Chunk(index=1, turn_id="turn-id", content=" world")),
    ]

    llm.stream.assert_awaited_once_with(
        messages=[
            Message(
                role=MessageRole.SYSTEM,
                content="Answer the user's latest message helpfully and accurately.",
            ),
            Message(role=MessageRole.USER, content="Hello"),
        ],
        onCreated=llm.stream.await_args.kwargs["onCreated"],
        onMessage=llm.stream.await_args.kwargs["onMessage"],
        onCompleted=llm.stream.await_args.kwargs["onCompleted"],
        onError=llm.stream.await_args.kwargs["onError"],
    )

    assert event_emitter.send.await_args_list == [
        call(id="public", event=EventCreated(turn_id="turn-id")),
        call(
            id="public",
            event=EventMessage(content="Hello", turn_id="turn-id", index=0),
        ),
        call(
            id="public",
            event=EventMessage(content=" world", turn_id="turn-id", index=1),
        ),
        call(id="public", event=EventCompleted(turn_id="turn-id")),
    ]


async def test_response_stream_error_emits_error_event() -> None:
    id_generator = mock_id_generator()

    existing_chat = Chat(
        id="chat-id-123",
        user_id="public",
        turns=[
            Turn(
                id="user-turn-id-123",
                type=TurnType.USER,
                content="Hello",
                status=TurnStatus.SUCCESS,
            ),
            Turn(
                id="turn-id",
                type=TurnType.ASSISTANT,
                content="",
                status=TurnStatus.PROCESSING,
            ),
        ],
    )
    chat_repo = mock_chat_repository()
    chat_repo.get_by_id.return_value = existing_chat
    chat_repo.update.return_value = existing_chat

    chunk_buffer_repo = mock_chunk_buffer_repository()
    llm = mock_llm_provider()
    event_emitter = mock_event_emitter()

    async def send_side_effect(*, id, event) -> None:
        if isinstance(event, EventError):
            # The error state and partial content must be persisted first.
            chat_repo.update_turn.assert_awaited_once()
            update_payload = chat_repo.update_turn.await_args.kwargs["turn"]
            assert update_payload.content == "Partial response"
            assert update_payload.status == TurnStatus.ERROR

    event_emitter.send.side_effect = send_side_effect

    async def stream_side_effect(
        *, messages, onCreated, onMessage, onCompleted, onError
    ) -> None:
        await onCreated()
        await onMessage("Partial ", 0)
        await onMessage("response", 1)
        await onError("Generation failed")

    llm.stream.side_effect = stream_side_effect

    use_cases = make_use_cases(
        chat_repo=chat_repo,
        chunk_buffer_repo=chunk_buffer_repo,
        id_generator=id_generator,
        llm=llm,
        event_emitter=event_emitter,
    )

    await use_cases.response(
        chat_id="chat-id-123", cot_id="cot-id-123", turn_id="turn-id"
    )

    chat_repo.get_by_id.assert_awaited_once_with(id="chat-id-123")

    chat_repo.update_turn.assert_awaited_once()
    update_call = chat_repo.update_turn.await_args
    assert update_call.kwargs["id"] == "chat-id-123"
    assert update_call.kwargs["turn_id"] == "turn-id"
    assert update_call.kwargs["turn"].content == "Partial response"
    assert update_call.kwargs["turn"].status == TurnStatus.ERROR

    assert chunk_buffer_repo.create.await_args_list == [
        call(Chunk(index=0, turn_id="turn-id", content="Partial ")),
        call(Chunk(index=1, turn_id="turn-id", content="response")),
    ]

    assert event_emitter.send.await_args_list == [
        call(id="public", event=EventCreated(turn_id="turn-id")),
        call(
            id="public",
            event=EventMessage(content="Partial ", turn_id="turn-id", index=0),
        ),
        call(
            id="public",
            event=EventMessage(content="response", turn_id="turn-id", index=1),
        ),
        call(
            id="public",
            event=EventError(
                message="Generation failed",
                turn_id="turn-id",
            ),
        ),
    ]


async def test_response_chat_not_found() -> None:
    chat_repo = mock_chat_repository()
    chat_repo.get_by_id.return_value = None
    id_generator = mock_id_generator()
    llm = mock_llm_provider()
    logger = mock_logger()
    event_emitter = mock_event_emitter()

    use_cases = make_use_cases(
        chat_repo=chat_repo,
        chunk_buffer_repo=mock_chunk_buffer_repository(),
        id_generator=id_generator,
        llm=llm,
        logger=logger,
        event_emitter=event_emitter,
    )

    with pytest.raises(DomainError) as exc_info:
        await use_cases.response(
            chat_id="chat-id-123", cot_id="cot-id-123", turn_id="turn-id"
        )

    error = exc_info.value
    assert error.type == ErrorType.NOT_FOUND
    assert error.msg == "AgentWorkerUseCases.response: Chat chat-id-123 not found"
    assert error.user_msg == "Failed to respond to missing chat"

    chat_repo.get_by_id.assert_awaited_once_with(id="chat-id-123")
    chat_repo.update.assert_not_awaited()
    llm.stream.assert_not_awaited()
    id_generator.gen.assert_not_called()
    logger.info.assert_not_called()
    event_emitter.send.assert_not_awaited()
