from datetime import UTC, datetime, timedelta

from lab.apps.bare_agent.shared.adapters.domain import (
    AgentWorkEntry,
)
from lab.apps.bare_agent.shared.adapters.infra.memory_work_scheduler import (
    InMemoryWorkScheduler,
)


class FakeClock:
    """A controllable clock for deterministic scheduler tests."""

    def __init__(self) -> None:
        self._now = datetime(2026, 1, 1, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self._now

    def advance(self, *, seconds: int) -> None:
        self._now += timedelta(seconds=seconds)


def make_entry(
    *,
    id: str = "entry-id",
    chat_id: str = "chat-id",
    turn_id: str = "turn-id",
    type: str = "response",
    payload: str = "payload",
) -> AgentWorkEntry[str]:
    return AgentWorkEntry(
        id=id,
        chat_id=chat_id,
        turn_id=turn_id,
        type=type,  # type: ignore[arg-type]
        payload=payload,
    )


def make_scheduler(
    *,
    lease_duration: timedelta = timedelta(seconds=10),
) -> tuple[InMemoryWorkScheduler[AgentWorkEntry[str]], FakeClock]:
    clock = FakeClock()
    scheduler = InMemoryWorkScheduler[AgentWorkEntry[str]](
        lease_duration=lease_duration,
        now=clock,
    )
    return scheduler, clock


async def test_add_returns_id_and_entry_can_be_claimed() -> None:
    scheduler, _ = make_scheduler()
    entry = make_entry()

    entry_id = await scheduler.add(entry)

    claim = await scheduler.claim()

    assert entry_id
    assert claim is not None
    assert claim.entry == entry
    assert claim.token
    assert claim.lease_until.tzinfo == UTC


async def test_claim_returns_none_when_scheduler_is_empty() -> None:
    scheduler, _ = make_scheduler()

    claim = await scheduler.claim()

    assert claim is None


async def test_claim_does_not_return_entry_with_active_lease() -> None:
    scheduler, _ = make_scheduler()
    entry = make_entry()
    await scheduler.add(entry)

    first_claim = await scheduler.claim()
    second_claim = await scheduler.claim()

    assert first_claim is not None
    assert first_claim.entry == entry
    assert second_claim is None


async def test_expired_lease_can_be_claimed_again() -> None:
    scheduler, clock = make_scheduler()
    entry = make_entry()
    await scheduler.add(entry)

    first_claim = await scheduler.claim()
    assert first_claim is not None

    clock.advance(seconds=10)

    second_claim = await scheduler.claim()

    assert second_claim is not None
    assert second_claim.entry == entry
    assert second_claim.token != first_claim.token


async def test_heartbeat_extends_active_lease() -> None:
    scheduler, clock = make_scheduler()
    await scheduler.add(make_entry())

    claim = await scheduler.claim()
    assert claim is not None

    clock.advance(seconds=5)

    heartbeat_succeeded = await scheduler.heartbeat(claim)

    assert heartbeat_succeeded is True

    # The original lease would have expired at t=10.
    clock.advance(seconds=6)

    next_claim = await scheduler.claim()

    assert next_claim is None


async def test_heartbeat_returns_false_for_expired_lease() -> None:
    scheduler, clock = make_scheduler()
    await scheduler.add(make_entry())

    claim = await scheduler.claim()
    assert claim is not None

    clock.advance(seconds=10)

    heartbeat_succeeded = await scheduler.heartbeat(claim)

    assert heartbeat_succeeded is False


async def test_ack_removes_claimed_entry() -> None:
    scheduler, _ = make_scheduler()
    await scheduler.add(make_entry())

    claim = await scheduler.claim()
    assert claim is not None

    await scheduler.ack(claim)

    next_claim = await scheduler.claim()

    assert next_claim is None


async def test_ack_does_not_remove_entry_after_lease_expires() -> None:
    scheduler, clock = make_scheduler()
    entry = make_entry()
    await scheduler.add(entry)

    first_claim = await scheduler.claim()
    assert first_claim is not None

    clock.advance(seconds=10)

    second_claim = await scheduler.claim()
    assert second_claim is not None

    await scheduler.ack(first_claim)

    # The stale claim must not remove the entry claimed by the second worker.
    next_claim = await scheduler.claim()

    assert next_claim is None

    await scheduler.ack(second_claim)

    assert await scheduler.claim() is None


async def test_retry_makes_entry_available_after_delay() -> None:
    scheduler, clock = make_scheduler()
    entry = make_entry()
    await scheduler.add(entry)

    claim = await scheduler.claim()
    assert claim is not None

    await scheduler.retry(claim, delay=5)

    # Entry is not available before the retry delay elapses.
    assert await scheduler.claim() is None

    clock.advance(seconds=5)

    retry_claim = await scheduler.claim()

    assert retry_claim is not None
    assert retry_claim.entry == entry
    assert retry_claim.token != claim.token


async def test_retry_does_not_release_entry_before_lease_expires() -> None:
    scheduler, clock = make_scheduler()
    entry = make_entry()
    await scheduler.add(entry)

    claim = await scheduler.claim()
    assert claim is not None

    clock.advance(seconds=10)

    await scheduler.retry(claim, delay=5)

    # The expired claim cannot modify the entry's state.
    retry_claim = await scheduler.claim()

    assert retry_claim is not None
    assert retry_claim.entry == entry


async def test_stale_claim_cannot_heartbeat_new_lease() -> None:
    scheduler, clock = make_scheduler()
    await scheduler.add(make_entry())

    first_claim = await scheduler.claim()
    assert first_claim is not None

    clock.advance(seconds=10)

    second_claim = await scheduler.claim()
    assert second_claim is not None

    heartbeat_succeeded = await scheduler.heartbeat(first_claim)

    assert heartbeat_succeeded is False

    # The stale claim must not affect the second claim's lease.
    clock.advance(seconds=1)

    assert await scheduler.claim() is None


async def test_retry_delay_is_respected_after_expired_claim_is_reclaimed() -> None:
    scheduler, clock = make_scheduler()
    entry = make_entry()
    await scheduler.add(entry)

    first_claim = await scheduler.claim()
    assert first_claim is not None

    clock.advance(seconds=10)

    second_claim = await scheduler.claim()
    assert second_claim is not None

    await scheduler.retry(second_claim, delay=5)

    assert await scheduler.claim() is None

    clock.advance(seconds=5)

    retry_claim = await scheduler.claim()

    assert retry_claim is not None
    assert retry_claim.entry == entry
