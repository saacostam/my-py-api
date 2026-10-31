import pytest

from lab.apps.bare_agent.features.agent.app import (
    AgentDecision,
    AgentWorkerUseCases,
)
from lab.apps.bare_agent.features.agent.test import (
    mock_chain_of_thought_repository,
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
from lab.apps.bare_agent.shared.adapters.domain import (
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

    user_id = "public"
    cot_id = "cot-id-123"

    user_turn = seed_turn(
        type=TurnType.USER,
        status=TurnStatus.SUCCESS,
    )
    assistant_turn = seed_turn(
        type=TurnType.ASSISTANT,
        status=TurnStatus.PROCESSING,
        content="",
    )

    existing_chat = seed_chat(
        user_id=user_id,
        turns=[
            user_turn,
            assistant_turn,
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

    await use_cases.decision(
        chat_id=existing_chat.id, cot_id=cot_id, turn_id=assistant_turn.id
    )

    chat_repo.get_by_id.assert_awaited_once_with(id=existing_chat.id)
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
            Message(role=MessageRole.USER, content=user_turn.content),
        ],
        output_schema=AgentDecision,
    )
    queue.add.assert_awaited_once_with(
        QueueEntry(
            id="queue-entry-id-123",
            chat_id=existing_chat.id,
            cot_id=cot_id,
            turn_id=assistant_turn.id,
            type="response",
        )
    )
    id_generator.gen.assert_called_once_with()


async def test_decision_tools_not_implemented() -> None:
    existing_chat = seed_chat()

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
        await use_cases.decision(
            chat_id=existing_chat.id, cot_id="cot-id-123", turn_id="turn-id"
        )

    queue.add.assert_not_awaited()
    id_generator.gen.assert_not_called()


async def test_decision_chat_not_found() -> None:
    chat_id = "chat-id-123"

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
        await use_cases.decision(
            chat_id=chat_id, cot_id="cot-id-123", turn_id="turn-id"
        )

    error = exc_info.value
    assert error.type == ErrorType.NOT_FOUND
    assert error.msg == f"AgentWorkerUseCases.decision: Chat {chat_id} not found"
    assert error.user_msg == "Failed to process missing chat"

    llm.generate.assert_not_awaited()
    queue.add.assert_not_awaited()
    id_generator.gen.assert_not_called()
    logger.info.assert_not_called()
