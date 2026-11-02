import asyncio
from typing import cast
from unittest.mock import AsyncMock

import pytest

from lab.apps.bare_agent.features.agent.test import (
    mock_agent_worker_use_cases,
)
from lab.apps.bare_agent.features.worker.app import WorkerProcessUseCase
from lab.apps.bare_agent.shared.adapters.domain import QueueEntry, QueueEntryType
from lab.apps.bare_agent.shared.adapters.test import (
    mock_logger,
    mock_queue,
)


def make_entry(type: QueueEntryType = "decision") -> QueueEntry:
    return QueueEntry(
        id="entry_id",
        chat_id="chat_id",
        cot_id="cot_id",
        turn_id="turn_id",
        type=type,
    )


def make_use_case(
    *,
    queue,
    agent_worker_use_cases,
    logger=None,
    sleep=None,
) -> WorkerProcessUseCase:
    return WorkerProcessUseCase(
        queue=queue,
        agent_worker_use_cases=agent_worker_use_cases,
        logger=logger or mock_logger(),
        sleep=sleep or AsyncMock(),
        poll_interval=0.1,
    )


async def stop_worker(sleep: AsyncMock) -> None:
    sleep.side_effect = asyncio.CancelledError


@pytest.mark.asyncio
@pytest.mark.parametrize("entry_type", ["decision", "response"])
async def test_run_processes_entry_and_removes_it(
    entry_type: QueueEntryType,
) -> None:
    queue = mock_queue()
    agent_worker_use_cases = mock_agent_worker_use_cases()
    sleep = AsyncMock()

    entry = make_entry(type=entry_type)
    queue.peek.side_effect = [entry, None]
    await stop_worker(sleep)

    use_case = make_use_case(
        queue=queue,
        agent_worker_use_cases=agent_worker_use_cases,
        sleep=sleep,
    )

    with pytest.raises(asyncio.CancelledError):
        await use_case.run()

    if entry_type == "decision":
        agent_worker_use_cases.decision.assert_awaited_once_with(
            chat_id=entry.chat_id,
            cot_id=entry.cot_id,
            turn_id=entry.turn_id,
        )
        agent_worker_use_cases.response.assert_not_awaited()
    else:
        agent_worker_use_cases.response.assert_awaited_once_with(
            chat_id=entry.chat_id,
            cot_id=entry.cot_id,
            turn_id=entry.turn_id,
        )
        agent_worker_use_cases.decision.assert_not_awaited()

    queue.remove.assert_awaited_once_with(id=entry.id)


@pytest.mark.asyncio
async def test_run_sleeps_when_queue_is_empty() -> None:
    queue = mock_queue()
    agent_worker_use_cases = mock_agent_worker_use_cases()
    sleep = AsyncMock()

    queue.peek.return_value = None
    await stop_worker(sleep)

    use_case = make_use_case(
        queue=queue,
        agent_worker_use_cases=agent_worker_use_cases,
        sleep=sleep,
    )

    with pytest.raises(asyncio.CancelledError):
        await use_case.run()

    sleep.assert_awaited_once_with(use_case.poll_interval)
    queue.remove.assert_not_awaited()
    agent_worker_use_cases.decision.assert_not_awaited()
    agent_worker_use_cases.response.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_logs_error_and_keeps_entry_when_processing_fails() -> None:
    queue = mock_queue()
    agent_worker_use_cases = mock_agent_worker_use_cases()
    logger = mock_logger()
    sleep = AsyncMock()

    entry = make_entry()
    queue.peek.side_effect = [entry, None]
    agent_worker_use_cases.decision.side_effect = RuntimeError("failure")
    await stop_worker(sleep)

    use_case = make_use_case(
        queue=queue,
        agent_worker_use_cases=agent_worker_use_cases,
        logger=logger,
        sleep=sleep,
    )

    with pytest.raises(asyncio.CancelledError):
        await use_case.run()

    queue.remove.assert_not_awaited()
    logger.error.assert_called_once_with(
        f"Failed to process queue entry {entry.id}; leaving it queued for retry"
    )


@pytest.mark.asyncio
async def test_run_logs_error_for_unsupported_entry_type() -> None:
    queue = mock_queue()
    agent_worker_use_cases = mock_agent_worker_use_cases()
    logger = mock_logger()
    sleep = AsyncMock()

    entry = make_entry(type=cast(QueueEntryType, "unsupported"))
    queue.peek.side_effect = [entry, None]
    await stop_worker(sleep)

    use_case = make_use_case(
        queue=queue,
        agent_worker_use_cases=agent_worker_use_cases,
        logger=logger,
        sleep=sleep,
    )

    with pytest.raises(asyncio.CancelledError):
        await use_case.run()

    queue.remove.assert_not_awaited()
    agent_worker_use_cases.decision.assert_not_awaited()
    agent_worker_use_cases.response.assert_not_awaited()
    logger.error.assert_called_once_with(
        f"Failed to process queue entry {entry.id}; leaving it queued for retry"
    )
