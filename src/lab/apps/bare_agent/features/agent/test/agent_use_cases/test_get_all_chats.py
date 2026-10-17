from lab.apps.bare_agent.features.agent.app import AgentUseCases
from lab.apps.bare_agent.features.agent.test import mock_chain_of_thought_repository
from lab.apps.bare_agent.features.chat.domain import (
    LeanChat,
)
from lab.apps.bare_agent.features.chat.test import (
    mock_chat_repository,
    mock_chunk_buffer_repository,
)
from lab.apps.bare_agent.shared.adapters.test import mock_id_generator, mock_queue


async def test_get_all_chats_success() -> None:
    chat_repo = mock_chat_repository()
    chats = [
        LeanChat(id="chat-id-123", user_id="public"),
        LeanChat(id="chat-id-456", user_id="public"),
    ]
    chat_repo.get_all_by_user_id.return_value = chats

    use_cases = AgentUseCases(
        chat_repo=chat_repo,
        chunk_buffer_repo=mock_chunk_buffer_repository(),
        cot_repo=mock_chain_of_thought_repository(),
        id_generator=mock_id_generator(),
        queue=mock_queue(),
    )

    result = await use_cases.get_all_chats()

    assert result == chats
    chat_repo.get_all_by_user_id.assert_awaited_once_with(
        user_id="public",
    )


async def test_get_all_chats_empty() -> None:
    chat_repo = mock_chat_repository()
    chat_repo.get_all_by_user_id.return_value = []

    use_cases = AgentUseCases(
        chat_repo=chat_repo,
        chunk_buffer_repo=mock_chunk_buffer_repository(),
        cot_repo=mock_chain_of_thought_repository(),
        id_generator=mock_id_generator(),
        queue=mock_queue(),
    )

    result = await use_cases.get_all_chats()

    assert result == []
    chat_repo.get_all_by_user_id.assert_awaited_once_with(
        user_id="public",
    )
