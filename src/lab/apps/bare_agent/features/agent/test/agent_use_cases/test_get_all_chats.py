from lab.apps.bare_agent.features.agent.app import AgentUseCases
from lab.apps.bare_agent.features.agent.test import mock_chain_of_thought_repository
from lab.apps.bare_agent.features.chat.test import (
    mock_chat_repository,
    mock_chunk_buffer_repository,
    seed_chat,
)
from lab.apps.bare_agent.shared.adapters.test import mock_id_generator, mock_queue


async def test_get_all_chats_success() -> None:
    user_id = "public"

    chats = [
        seed_chat(user_id=user_id),
        seed_chat(user_id=user_id),
    ]

    chat_repo = mock_chat_repository()
    chat_repo.get_all_by_user_id.return_value = chats

    use_cases = AgentUseCases(
        chat_repo=chat_repo,
        chunk_buffer_repo=mock_chunk_buffer_repository(),
        cot_repo=mock_chain_of_thought_repository(),
        id_generator=mock_id_generator(),
        queue=mock_queue(),
    )

    result = await use_cases.get_all_chats(user_id=user_id)

    assert result == chats
    chat_repo.get_all_by_user_id.assert_awaited_once_with(
        user_id=user_id,
    )


async def test_get_all_chats_empty() -> None:
    user_id = "public"

    chat_repo = mock_chat_repository()
    chat_repo.get_all_by_user_id.return_value = []

    use_cases = AgentUseCases(
        chat_repo=chat_repo,
        chunk_buffer_repo=mock_chunk_buffer_repository(),
        cot_repo=mock_chain_of_thought_repository(),
        id_generator=mock_id_generator(),
        queue=mock_queue(),
    )

    result = await use_cases.get_all_chats(user_id=user_id)

    assert result == []
    chat_repo.get_all_by_user_id.assert_awaited_once_with(
        user_id=user_id,
    )
