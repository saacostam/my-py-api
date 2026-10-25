from lab.apps.bare_agent.features.agent.app import (
    AgentUseCases,
    ChatDetails,
    SuccessTurn,
)
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
from lab.apps.bare_agent.shared.adapters.test import mock_id_generator, mock_queue
from lab.shared.errors.domain import DomainError, ErrorType


async def test_get_by_id_success() -> None:
    chat_repo = mock_chat_repository()
    chunk_buffer_repo = mock_chunk_buffer_repository()
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

    use_cases = AgentUseCases(
        chat_repo=chat_repo,
        chunk_buffer_repo=chunk_buffer_repo,
        cot_repo=mock_chain_of_thought_repository(),
        id_generator=mock_id_generator(),
        queue=mock_queue(),
    )

    result = await use_cases.get_by_id(chat_id="chat-id-123", user_id="public")

    assert result == ChatDetails(
        id="chat-id-123",
        user_id="public",
        turns=[
            SuccessTurn(
                id="turn-id-123",
                type=TurnType.USER,
                status=TurnStatus.SUCCESS,
                content="Hello",
            )
        ],
    )
    chat_repo.get_by_id.assert_awaited_once_with(id="chat-id-123")
    chunk_buffer_repo.get_all_by_turn_ids.assert_not_awaited()


async def test_get_by_id_chat_not_found() -> None:
    chat_repo = mock_chat_repository()
    chunk_buffer_repo = mock_chunk_buffer_repository()
    chat_repo.get_by_id.return_value = None

    cot_repo = mock_chain_of_thought_repository()
    id_generator = mock_id_generator()
    queue = mock_queue()

    use_cases = AgentUseCases(
        chat_repo=chat_repo,
        chunk_buffer_repo=chunk_buffer_repo,
        cot_repo=cot_repo,
        id_generator=id_generator,
        queue=queue,
    )

    try:
        await use_cases.get_by_id(chat_id="chat-id-123", user_id="public")
        assert False, "Expected DomainError"
    except DomainError as error:
        assert error.type == ErrorType.NOT_FOUND
        assert error.msg == "Chat was not found"
        assert error.user_msg == "Chat with id chat-id-123 was not found"

    chat_repo.get_by_id.assert_awaited_once_with(id="chat-id-123")
    chunk_buffer_repo.get_all_by_turn_ids.assert_not_awaited()
    cot_repo.create.assert_not_awaited()
    queue.add.assert_not_awaited()
    id_generator.gen.assert_not_called()


async def test_get_by_id_chat_is_not_from_user() -> None:
    chat_repo = mock_chat_repository()
    chunk_buffer_repo = mock_chunk_buffer_repository()

    existing_chat = Chat(
        id="chat-id-123",
        user_id="another-user",
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

    cot_repo = mock_chain_of_thought_repository()
    id_generator = mock_id_generator()
    queue = mock_queue()

    use_cases = AgentUseCases(
        chat_repo=chat_repo,
        chunk_buffer_repo=chunk_buffer_repo,
        cot_repo=cot_repo,
        id_generator=id_generator,
        queue=queue,
    )

    try:
        await use_cases.get_by_id(chat_id="chat-id-123", user_id="public")
        assert False, "Expected DomainError"
    except DomainError as error:
        assert error.type == ErrorType.NOT_FOUND
        assert error.msg == "Chat was not found"
        assert error.user_msg == "Chat with id chat-id-123 was not found"

    chat_repo.get_by_id.assert_awaited_once_with(id="chat-id-123")
    chunk_buffer_repo.get_all_by_turn_ids.assert_not_awaited()
    cot_repo.create.assert_not_awaited()
    queue.add.assert_not_awaited()
    id_generator.gen.assert_not_called()
