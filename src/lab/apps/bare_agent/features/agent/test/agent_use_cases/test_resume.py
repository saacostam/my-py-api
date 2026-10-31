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
from lab.shared.errors.domain import DomainError, ErrorType


async def test_resume_agent_success() -> None:
    old_turn = seed_turn()
    created_user_turn = seed_turn(
        type=TurnType.USER,
        status=TurnStatus.SUCCESS,
    )
    created_assistant_turn = seed_turn(
        type=TurnType.ASSISTANT,
        status=TurnStatus.PROCESSING,
        content="",
    )

    existing_chat = seed_chat(turns=[old_turn])
    chat_repo = mock_chat_repository()
    chat_repo.get_by_id.return_value = existing_chat
    chat_repo.update.return_value = existing_chat

    created_cot = seed_chain_of_thought(
        chat_id=existing_chat.id,
        objective=f"Answer this message from the user: {created_user_turn.content}",
    )
    cot_repo = mock_chain_of_thought_repository()
    cot_repo.create.return_value = created_cot

    id_generator = mock_id_generator()
    id_generator.gen.side_effect = [
        created_user_turn.id,
        created_assistant_turn.id,
        created_cot.id,
        "queue-entry-id-123",
    ]

    queue = mock_queue()

    use_cases = AgentUseCases(
        chat_repo=chat_repo,
        chunk_buffer_repo=mock_chunk_buffer_repository(),
        cot_repo=cot_repo,
        id_generator=id_generator,
        queue=queue,
    )

    result = await use_cases.resume(
        chat_id=existing_chat.id,
        message=created_user_turn.content,
        user_id=existing_chat.user_id,
    )

    assert result == ChatIdentifier(chat_id=existing_chat.id)

    chat_repo.get_by_id.assert_awaited_once_with(id=existing_chat.id)

    assert existing_chat.turns == [
        old_turn,
        created_user_turn,
        created_assistant_turn,
    ]

    chat_repo.update.assert_awaited_once_with(
        chat_id=existing_chat.id,
        chat=existing_chat,
    )

    cot_repo.create.assert_awaited_once_with(created_cot)

    queue.add.assert_awaited_once_with(
        QueueEntry(
            id="queue-entry-id-123",
            chat_id=existing_chat.id,
            cot_id=created_cot.id,
            turn_id=created_assistant_turn.id,
            type="decision",
        )
    )

    assert id_generator.gen.call_count == 4


async def test_resume_agent_chat_not_found() -> None:
    chat_id = "chat-id-123"
    user_id = "public"

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
        await use_cases.resume(chat_id=chat_id, message="How are you?", user_id=user_id)
        assert False, "Expected DomainError"
    except DomainError as error:
        assert error.type == ErrorType.NOT_FOUND
        assert error.msg == "Chat was not found"
        assert error.user_msg == f"Chat with id {chat_id} was not found"

    chat_repo.get_by_id.assert_awaited_once_with(id=chat_id)
    cot_repo.create.assert_not_awaited()
    queue.add.assert_not_awaited()
    id_generator.gen.assert_not_called()


async def test_resume_agent_chat_belongs_to_different_user() -> None:
    user_id = "user-id"
    not_user_id = "other-user-id"

    existing_chat = seed_chat(user_id=not_user_id)
    chat_repo = mock_chat_repository()
    chat_repo.get_by_id.return_value = existing_chat

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
            chat_id=existing_chat.id,
            message="How are you?",
            user_id=user_id,
        )
        assert False, "Expected DomainError"
    except DomainError as error:
        assert error.type == ErrorType.NOT_FOUND
        assert error.msg == "Chat was not found"
        assert error.user_msg == f"Chat with id {existing_chat.id} was not found"

    chat_repo.get_by_id.assert_awaited_once_with(id=existing_chat.id)
    cot_repo.create.assert_not_awaited()
    queue.add.assert_not_awaited()
    id_generator.gen.assert_not_called()
