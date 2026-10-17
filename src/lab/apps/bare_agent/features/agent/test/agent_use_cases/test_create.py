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


async def test_create_agent_success() -> None:
    id_generator = mock_id_generator()
    id_generator.gen.side_effect = [
        "chat-id-123",
        "turn-id-123",
        "cot-id-123",
        "queue-entry-id-123",
    ]

    chat_repo = mock_chat_repository()
    created_chat = Chat(
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
    chat_repo.create.return_value = created_chat

    cot_repo = mock_chain_of_thought_repository()
    created_cot = ChainOfThought(
        id="cot-id-123",
        chat_id="chat-id-123",
        objective="Answer this message from the user: $Hello",
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

    result = await use_cases.create(message="Hello")

    assert result == ChatIdentifier(chat_id="chat-id-123")

    chat_repo.create.assert_awaited_once_with(chat=created_chat)

    cot_repo.create.assert_awaited_once_with(created_cot)

    queue.add.assert_awaited_once_with(
        QueueEntry(
            id="queue-entry-id-123",
            chat_id="chat-id-123",
            cot_id="cot-id-123",
            type="decision",
        )
    )

    assert id_generator.gen.call_count == 4
