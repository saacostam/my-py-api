from lab.apps.bare_agent.features.agent.app import AgentUseCases, ChatIdentifier
from lab.apps.bare_agent.features.agent.domain import ChainOfThought
from lab.apps.bare_agent.features.agent.test import mock_chain_of_thought_repository
from lab.apps.bare_agent.features.chat.domain import (
    Chat,
    Turn,
    TurnStatus,
    TurnType,
)
from lab.apps.bare_agent.features.chat.test import (
    mock_chat_repository,
    mock_chunk_buffer_repository,
)
from lab.apps.bare_agent.shared.adapters.domain import QueueEntry
from lab.apps.bare_agent.shared.adapters.test import mock_id_generator, mock_queue
from lab.shared.errors.domain import DomainError, ErrorType


async def test_resume_agent_success() -> None:
    id_generator = mock_id_generator()
    id_generator.gen.side_effect = [
        "turn-id-456",
        "turn-id-789",
        "cot-id-123",
        "queue-entry-id-123",
    ]

    chat_repo = mock_chat_repository()
    existing_chat = Chat(
        id="chat-id-123",
        user_id="public",
        turns=[
            Turn(
                id="turn-id-123",
                type=TurnType.USER,
                content="Hello",
                status=TurnStatus.SUCCESS,
            )
        ],
    )
    chat_repo.get_by_id.return_value = existing_chat
    chat_repo.update.return_value = existing_chat

    cot_repo = mock_chain_of_thought_repository()
    created_cot = ChainOfThought(
        id="cot-id-123",
        chat_id="chat-id-123",
        objective="Answer this message from the user: $How are you?",
        thoughts=[],
    )
    cot_repo.create.return_value = created_cot

    queue = mock_queue()

    use_cases = AgentUseCases(
        chat_repo=chat_repo,
        chunk_buffer_repo=mock_chunk_buffer_repository(),
        cot_repo=cot_repo,
        id_generator=id_generator,
        queue=queue,
    )

    result = await use_cases.resume(
        chat_id="chat-id-123",
        message="How are you?",
    )

    assert result == ChatIdentifier(chat_id="chat-id-123")

    chat_repo.get_by_id.assert_awaited_once_with(id="chat-id-123")

    assert existing_chat.turns == [
        Turn(
            id="turn-id-123",
            type=TurnType.USER,
            content="Hello",
            status=TurnStatus.SUCCESS,
        ),
        Turn(
            id="turn-id-456",
            type=TurnType.USER,
            content="How are you?",
            status=TurnStatus.SUCCESS,
        ),
        Turn(
            id="turn-id-789",
            type=TurnType.ASSISTANT,
            content="",
            status=TurnStatus.PROCESSING,
        ),
    ]

    chat_repo.update.assert_awaited_once_with(
        chat_id="chat-id-123",
        chat=existing_chat,
    )

    cot_repo.create.assert_awaited_once_with(created_cot)

    queue.add.assert_awaited_once_with(
        QueueEntry(
            id="queue-entry-id-123",
            chat_id="chat-id-123",
            cot_id="cot-id-123",
            turn_id="turn-id-789",
            type="decision",
        )
    )

    assert id_generator.gen.call_count == 4


async def test_resume_agent_chat_not_found() -> None:
    chat_repo = mock_chat_repository()
    chat_repo.get_by_id.return_value = None

    cot_repo = mock_chain_of_thought_repository()
    id_generator = mock_id_generator()
    queue = mock_queue()

    use_cases = AgentUseCases(
        chat_repo=chat_repo,
        chunk_buffer_repo=mock_chunk_buffer_repository(),
        cot_repo=cot_repo,
        id_generator=id_generator,
        queue=queue,
    )

    try:
        await use_cases.resume(
            chat_id="chat-id-123",
            message="How are you?",
        )
        assert False, "Expected DomainError"
    except DomainError as error:
        assert error.type == ErrorType.NOT_FOUND
        assert error.msg == "Chat was not found"
        assert error.user_msg == "Chat with id chat-id-123 was not found"

    chat_repo.get_by_id.assert_awaited_once_with(id="chat-id-123")
    cot_repo.create.assert_not_awaited()
    queue.add.assert_not_awaited()
    id_generator.gen.assert_not_called()
