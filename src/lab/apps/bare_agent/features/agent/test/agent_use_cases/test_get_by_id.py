from lab.apps.bare_agent.features.agent.app import (
    AgentUseCases,
    ChatDetails,
    SuccessTurn,
)
from lab.apps.bare_agent.features.agent.test import mock_chain_of_thought_repository
from lab.apps.bare_agent.features.chat.domain import (
    TurnStatus,
)
from lab.apps.bare_agent.features.chat.test import (
    mock_chat_repository,
    mock_chunk_buffer_repository,
    seed_chat,
    seed_turn,
)
from lab.apps.bare_agent.shared.adapters.test import mock_id_generator, mock_queue
from lab.shared.errors.domain import DomainError, ErrorType


async def test_get_by_id_success() -> None:
    chat_repo = mock_chat_repository()
    chunk_buffer_repo = mock_chunk_buffer_repository()

    turn = seed_turn()

    existing_chat = seed_chat(turns=[turn])
    chat_repo.get_by_id.return_value = existing_chat

    use_cases = AgentUseCases(
        chat_repo=chat_repo,
        chunk_buffer_repo=chunk_buffer_repo,
        cot_repo=mock_chain_of_thought_repository(),
        id_generator=mock_id_generator(),
        queue=mock_queue(),
    )

    result = await use_cases.get_by_id(
        chat_id=existing_chat.id, user_id=existing_chat.user_id
    )

    assert result == ChatDetails(
        id=existing_chat.id,
        user_id=existing_chat.user_id,
        turns=[
            SuccessTurn(
                id=turn.id,
                type=turn.type,
                status=TurnStatus.SUCCESS,
                content=turn.content,
            )
        ],
    )
    chat_repo.get_by_id.assert_awaited_once_with(id=existing_chat.id)
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

    chat_id = "chat-id-123"
    user_id = "public"

    try:
        await use_cases.get_by_id(chat_id=chat_id, user_id=user_id)
        assert False, "Expected DomainError"
    except DomainError as error:
        assert error.type == ErrorType.NOT_FOUND
        assert error.msg == "Chat was not found"
        assert error.user_msg == f"Chat with id {chat_id} was not found"

    chat_repo.get_by_id.assert_awaited_once_with(id=chat_id)
    chunk_buffer_repo.get_all_by_turn_ids.assert_not_awaited()
    cot_repo.create.assert_not_awaited()
    queue.add.assert_not_awaited()
    id_generator.gen.assert_not_called()


async def test_get_by_id_chat_is_not_from_user() -> None:
    user_id = "public"
    not_user_id = "not-user-id"

    chat_repo = mock_chat_repository()
    chunk_buffer_repo = mock_chunk_buffer_repository()

    turn = seed_turn()

    existing_chat = seed_chat(turns=[turn], user_id=user_id)
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
        await use_cases.get_by_id(chat_id=existing_chat.id, user_id=not_user_id)
        assert False, "Expected DomainError"
    except DomainError as error:
        assert error.type == ErrorType.NOT_FOUND
        assert error.msg == "Chat was not found"
        assert error.user_msg == f"Chat with id {existing_chat.id} was not found"

    chat_repo.get_by_id.assert_awaited_once_with(id=existing_chat.id)
    chunk_buffer_repo.get_all_by_turn_ids.assert_not_awaited()
    cot_repo.create.assert_not_awaited()
    queue.add.assert_not_awaited()
    id_generator.gen.assert_not_called()
