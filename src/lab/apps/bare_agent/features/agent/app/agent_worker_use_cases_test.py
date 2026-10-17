from unittest.mock import call

import pytest

from lab.apps.bare_agent.features.agent.app import (
    AgentDecision,
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
    QueueEntry,
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


async def test_decision_response_success() -> None:
    id_generator = mock_id_generator()
    id_generator.gen.return_value = "queue-entry-id-123"

    existing_chat = Chat(
        id="chat-id-123",
        user_id="public",
        turns=[
            Turn(
                id="user-turn-id-123",
                type=TurnType.USER,
                content="Hello",
                status=TurnStatus.SUCCESS,
            )
        ],
    )

    chat_repo = mock_chat_repository()
    chat_repo.get_by_id.return_value = existing_chat

    llm = mock_llm_provider()
    llm.generate.return_value = AgentDecision(decision="response")
    queue = mock_queue()

    use_cases = make_use_cases(
        chat_repo=chat_repo,
        chunk_buffer_repo=mock_chunk_buffer_repository(),
        id_generator=id_generator,
        llm=llm,
        queue=queue,
    )

    await use_cases.decision(chat_id="chat-id-123", cot_id="cot-id-123")

    chat_repo.get_by_id.assert_awaited_once_with(id="chat-id-123")
    llm.generate.assert_awaited_once_with(
        messages=[
            Message(
                role=MessageRole.SYSTEM,
                content=(
                    "Decide whether the user's request can be answered "
                    "directly or requires tools. Choose 'response' for a "
                    "direct answer and 'tools' when tools are necessary."
                ),
            ),
            Message(role=MessageRole.USER, content="Hello"),
        ],
        output_schema=AgentDecision,
    )
    queue.add.assert_awaited_once_with(
        QueueEntry(
            id="queue-entry-id-123",
            chat_id="chat-id-123",
            cot_id="cot-id-123",
            type="response",
        )
    )
    id_generator.gen.assert_called_once_with()


async def test_decision_tools_not_implemented() -> None:
    existing_chat = Chat(
        id="chat-id-123",
        user_id="public",
        turns=[
            Turn(
                id="user-turn-id-123",
                type=TurnType.USER,
                content="Search for something",
                status=TurnStatus.SUCCESS,
            )
        ],
    )
    chat_repo = mock_chat_repository()
    chat_repo.get_by_id.return_value = existing_chat
    llm = mock_llm_provider()
    llm.generate.return_value = AgentDecision(decision="tools")
    id_generator = mock_id_generator()
    queue = mock_queue()

    use_cases = make_use_cases(
        chat_repo=chat_repo,
        chunk_buffer_repo=mock_chunk_buffer_repository(),
        id_generator=id_generator,
        llm=llm,
        queue=queue,
    )

    with pytest.raises(
        NotImplementedError,
        match="Tool execution is not implemented",
    ):
        await use_cases.decision(chat_id="chat-id-123", cot_id="cot-id-123")

    queue.add.assert_not_awaited()
    id_generator.gen.assert_not_called()


async def test_decision_chat_not_found() -> None:
    chat_repo = mock_chat_repository()
    chat_repo.get_by_id.return_value = None
    llm = mock_llm_provider()
    id_generator = mock_id_generator()
    logger = mock_logger()
    queue = mock_queue()

    use_cases = make_use_cases(
        chat_repo=chat_repo,
        chunk_buffer_repo=mock_chunk_buffer_repository(),
        id_generator=id_generator,
        llm=llm,
        logger=logger,
        queue=queue,
    )

    with pytest.raises(DomainError) as exc_info:
        await use_cases.decision(chat_id="chat-id-123", cot_id="cot-id-123")

    error = exc_info.value
    assert error.type == ErrorType.NOT_FOUND
    assert error.msg == "AgentWorkerUseCases.decision: Chat chat-id-123 not found"
    assert error.user_msg == "Failed to process missing chat"

    llm.generate.assert_not_awaited()
    queue.add.assert_not_awaited()
    id_generator.gen.assert_not_called()
    logger.info.assert_not_called()


async def test_response_success() -> None:
    id_generator = mock_id_generator()
    id_generator.gen.return_value = "turn-id-123"

    existing_chat = Chat(
        id="chat-id-123",
        user_id="public",
        turns=[
            Turn(
                id="user-turn-id-123",
                type=TurnType.USER,
                content="Hello",
                status=TurnStatus.SUCCESS,
            )
        ],
    )
    chat_repo = mock_chat_repository()
    chat_repo.get_by_id.return_value = existing_chat
    chat_repo.update.return_value = existing_chat

    chunk_buffer_repo = mock_chunk_buffer_repository()
    llm = mock_llm_provider()
    event_emitter = mock_event_emitter()

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

    await use_cases.response(chat_id="chat-id-123", cot_id="cot-id-123")

    chat_repo.get_by_id.assert_awaited_once_with(id="chat-id-123")
    assert chat_repo.update.await_count == 2
    assert all(
        update_call.kwargs == {"chat_id": "chat-id-123", "chat": existing_chat}
        for update_call in chat_repo.update.await_args_list
    )
    assert existing_chat.turns[-1] == Turn(
        id="turn-id-123",
        type=TurnType.ASSISTANT,
        content="",
        status=TurnStatus.SUCCESS,
    )

    assert chunk_buffer_repo.create.await_args_list == [
        call(Chunk(index=0, turn_id="turn-id-123", content="Hello")),
        call(Chunk(index=1, turn_id="turn-id-123", content=" world")),
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
        call(id="public", event=EventCreated(turn_id="turn-id-123")),
        call(
            id="public",
            event=EventMessage(content="Hello", turn_id="turn-id-123"),
        ),
        call(
            id="public",
            event=EventMessage(content=" world", turn_id="turn-id-123"),
        ),
        call(id="public", event=EventCompleted(turn_id="turn-id-123")),
    ]
    id_generator.gen.assert_called_once_with()


async def test_response_stream_error_emits_error_event() -> None:
    id_generator = mock_id_generator()
    id_generator.gen.return_value = "turn-id-123"

    existing_chat = Chat(
        id="chat-id-123",
        user_id="public",
        turns=[
            Turn(
                id="user-turn-id-123",
                type=TurnType.USER,
                content="Hello",
                status=TurnStatus.SUCCESS,
            )
        ],
    )
    chat_repo = mock_chat_repository()
    chat_repo.get_by_id.return_value = existing_chat
    chat_repo.update.return_value = existing_chat

    chunk_buffer_repo = mock_chunk_buffer_repository()
    llm = mock_llm_provider()
    event_emitter = mock_event_emitter()

    async def stream_side_effect(
        *, messages, onCreated, onMessage, onCompleted, onError
    ) -> None:
        await onCreated()
        await onError("Generation failed")

    llm.stream.side_effect = stream_side_effect

    use_cases = make_use_cases(
        chat_repo=chat_repo,
        chunk_buffer_repo=chunk_buffer_repo,
        id_generator=id_generator,
        llm=llm,
        event_emitter=event_emitter,
    )

    await use_cases.response(chat_id="chat-id-123", cot_id="cot-id-123")

    assert chat_repo.update.await_count == 2
    assert existing_chat.turns[-1] == Turn(
        id="turn-id-123",
        type=TurnType.ASSISTANT,
        content="",
        status=TurnStatus.ERROR,
    )
    chunk_buffer_repo.create.assert_not_awaited()
    assert event_emitter.send.await_args_list == [
        call(id="public", event=EventCreated(turn_id="turn-id-123")),
        call(
            id="public",
            event=EventError(message="Generation failed", turn_id="turn-id-123"),
        ),
    ]
    id_generator.gen.assert_called_once_with()


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
        await use_cases.response(chat_id="chat-id-123", cot_id="cot-id-123")

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
