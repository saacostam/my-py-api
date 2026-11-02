import asyncio
from datetime import UTC, datetime
from typing import cast
from unittest.mock import AsyncMock

import pytest

from lab.apps.bare_agent.features.agent.test import (
    mock_agent_worker_use_cases,
)
from lab.apps.bare_agent.features.worker.app import WorkerProcessUseCase
from lab.apps.bare_agent.shared.adapters.domain import (
    AgentWorkEntry,
    AgentWorkEntryType,
    Claim,
)
from lab.apps.bare_agent.shared.adapters.test import mock_logger


def make_entry(
    type: AgentWorkEntryType = "decision",
) -> AgentWorkEntry:
    return AgentWorkEntry(
        id="entry_id",
        chat_id="chat_id",
        cot_id="cot_id",
        turn_id="turn_id",
        type=type,
    )


def make_claim(
    entry: AgentWorkEntry,
    *,
    token: str = "claim_token",
) -> Claim[AgentWorkEntry]:
    return Claim(
        entry=entry,
        token=token,
        lease_until=datetime(2026, 1, 1, tzinfo=UTC),
    )


def make_use_case(
    *,
    scheduler,
    agent_worker_use_cases,
    logger=None,
    sleep=None,
) -> WorkerProcessUseCase:
    return WorkerProcessUseCase(
        scheduler=scheduler,
        agent_worker_use_cases=agent_worker_use_cases,
        logger=logger or mock_logger(),
        sleep=sleep or AsyncMock(),
        poll_interval=0.1,
        retry_delay=1,
    )


async def stop_worker(sleep: AsyncMock) -> None:
    sleep.side_effect = asyncio.CancelledError


@pytest.mark.asyncio
@pytest.mark.parametrize("entry_type", ["decision", "response"])
async def test_run_processes_entry_and_acknowledges_claim(
    entry_type: AgentWorkEntryType,
) -> None:
    scheduler = AsyncMock()
    agent_worker_use_cases = mock_agent_worker_use_cases()
    sleep = AsyncMock()

    entry = make_entry(type=entry_type)
    claim = make_claim(entry)

    scheduler.claim.side_effect = [claim, None]
    await stop_worker(sleep)

    use_case = make_use_case(
        scheduler=scheduler,
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

    scheduler.ack.assert_awaited_once_with(claim)
    scheduler.retry.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_sleeps_when_scheduler_is_empty() -> None:
    scheduler = AsyncMock()
    agent_worker_use_cases = mock_agent_worker_use_cases()
    sleep = AsyncMock()

    scheduler.claim.return_value = None
    await stop_worker(sleep)

    use_case = make_use_case(
        scheduler=scheduler,
        agent_worker_use_cases=agent_worker_use_cases,
        sleep=sleep,
    )

    with pytest.raises(asyncio.CancelledError):
        await use_case.run()

    sleep.assert_awaited_once_with(use_case.poll_interval)
    scheduler.ack.assert_not_awaited()
    scheduler.retry.assert_not_awaited()
    agent_worker_use_cases.decision.assert_not_awaited()
    agent_worker_use_cases.response.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_logs_error_and_retries_when_processing_fails() -> None:
    scheduler = AsyncMock()
    agent_worker_use_cases = mock_agent_worker_use_cases()
    logger = mock_logger()
    sleep = AsyncMock()

    entry = make_entry()
    claim = make_claim(entry)

    scheduler.claim.side_effect = [claim, None]
    agent_worker_use_cases.decision.side_effect = RuntimeError("failure")
    await stop_worker(sleep)

    use_case = make_use_case(
        scheduler=scheduler,
        agent_worker_use_cases=agent_worker_use_cases,
        logger=logger,
        sleep=sleep,
    )

    with pytest.raises(asyncio.CancelledError):
        await use_case.run()

    scheduler.ack.assert_not_awaited()
    scheduler.retry.assert_awaited_once_with(claim, delay=use_case.retry_delay)
    logger.error.assert_called_once_with(
        f"Failed to process work entry {entry.id}; scheduling it for retry"
    )


@pytest.mark.asyncio
async def test_run_logs_error_for_unsupported_entry_type() -> None:
    scheduler = AsyncMock()
    agent_worker_use_cases = mock_agent_worker_use_cases()
    logger = mock_logger()
    sleep = AsyncMock()

    entry = make_entry(type=cast(AgentWorkEntryType, "unsupported"))
    claim = make_claim(entry)

    scheduler.claim.side_effect = [claim, None]
    await stop_worker(sleep)

    use_case = make_use_case(
        scheduler=scheduler,
        agent_worker_use_cases=agent_worker_use_cases,
        logger=logger,
        sleep=sleep,
    )

    with pytest.raises(asyncio.CancelledError):
        await use_case.run()

    scheduler.ack.assert_not_awaited()
    scheduler.retry.assert_awaited_once_with(claim, delay=use_case.retry_delay)
    agent_worker_use_cases.decision.assert_not_awaited()
    agent_worker_use_cases.response.assert_not_awaited()
    logger.error.assert_called_once_with(
        f"Failed to process work entry {entry.id}; scheduling it for retry"
    )
