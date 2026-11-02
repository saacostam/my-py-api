from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from lab.apps.bare_agent.shared.adapters.domain import Claim


@dataclass
class _ScheduledItem[T]:
    """Internal state for a scheduled work entry."""

    id: str
    entry: T
    available_at: datetime
    token: str | None = None
    lease_until: datetime | None = None


class InMemoryWorkScheduler[T]:
    def __init__(
        self,
        lease_duration: timedelta,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._lease_duration = lease_duration
        self._now = now
        self._items: list[_ScheduledItem[T]] = []

    async def add(self, entry: T) -> str:
        item_id = str(uuid4())

        self._items.append(
            _ScheduledItem(
                id=item_id,
                entry=entry,
                available_at=self._now(),
            )
        )

        return item_id

    async def claim(self) -> Claim[T] | None:
        now = self._now()

        for item in self._items:
            if item.available_at > now:
                continue

            if (
                item.token is not None
                and item.lease_until is not None
                and item.lease_until > now
            ):
                continue

            token = str(uuid4())
            lease_until = now + self._lease_duration

            item.token = token
            item.lease_until = lease_until

            return Claim(
                entry=item.entry,
                token=token,
                lease_until=lease_until,
            )

        return None

    async def heartbeat(self, claim: Claim[T]) -> bool:
        now = self._now()

        for item in self._items:
            if item.token != claim.token:
                continue

            if item.lease_until is None or item.lease_until <= now:
                return False

            item.lease_until = now + self._lease_duration
            return True

        return False

    async def ack(self, claim: Claim[T]) -> None:
        now = self._now()

        for index, item in enumerate(self._items):
            if item.token != claim.token:
                continue

            if item.lease_until is None or item.lease_until <= now:
                return

            self._items.pop(index)
            return

    async def retry(self, claim: Claim[T], *, delay: int) -> None:
        now = self._now()

        for item in self._items:
            if item.token != claim.token:
                continue

            if item.lease_until is None or item.lease_until <= now:
                return

            item.token = None
            item.lease_until = None
            item.available_at = now + timedelta(seconds=delay)
            return
