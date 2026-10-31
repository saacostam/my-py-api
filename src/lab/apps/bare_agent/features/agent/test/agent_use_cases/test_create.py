from lab.apps.bare_agent.features.agent.app import AgentUseCases, ChatIdentifier
from lab.apps.bare_agent.features.agent.test import (
    mock_chain_of_thought_repository,
    seed_chain_of_thought,
)
from lab.apps.bare_agent.features.chat.domain import (
    TurnStatus,
    TurnType,
)
from lab.apps.bare_agent.features.chat.test import (
    mock_chat_repository,
    mock_chunk_buffer_repository,
    seed_chat,
    seed_turn,
)
from lab.apps.bare_agent.shared.adapters.domain import QueueEntry
from lab.apps.bare_agent.shared.adapters.test import mock_id_generator, mock_queue


async def test_create_agent_success() -> None:
    user_message = seed_turn(
        type=TurnType.USER,
    )
    assistant_message = seed_turn(
        content="", status=TurnStatus.PROCESSING, type=TurnType.ASSISTANT
    )

    created_chat = seed_chat(
        turns=[
            user_message,
            assistant_message,
        ]
    )

    created_cot = seed_chain_of_thought(
        chat_id=created_chat.id,
        objective=f"Answer this message from the user: {user_message.content}",
        thoughts=[],
    )

    id_generator = mock_id_generator()
    id_generator.gen.side_effect = [
        created_chat.id,
        user_message.id,
        assistant_message.id,
        created_cot.id,
        "queue-entry-id-123",
    ]

    chat_repo = mock_chat_repository()
    chat_repo.create.return_value = created_chat

    cot_repo = mock_chain_of_thought_repository()
    cot_repo.create.return_value = created_cot

    queue = mock_queue()

    use_cases = AgentUseCases(
        chat_repo=chat_repo,
        chunk_buffer_repo=mock_chunk_buffer_repository(),
        cot_repo=cot_repo,
        id_generator=id_generator,
        queue=queue,
    )

    result = await use_cases.create(
        message=user_message.content, user_id=created_chat.user_id
    )

    assert result == ChatIdentifier(chat_id=created_chat.id)

    chat_repo.create.assert_awaited_once_with(chat=created_chat)

    cot_repo.create.assert_awaited_once_with(created_cot)

    queue.add.assert_awaited_once_with(
        QueueEntry(
            id="queue-entry-id-123",
            chat_id=created_chat.id,
            cot_id=created_cot.id,
            turn_id=assistant_message.id,
            type="decision",
        )
    )

    assert id_generator.gen.call_count == 5
