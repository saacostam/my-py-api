from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol


@dataclass(frozen=True)
class Claim[T]:
    entry: T
    token: str
    lease_until: datetime


class WorkScheduler[T](Protocol):
    async def add(self, entry: T) -> str:
        """Add an entry to the scheduler and return its ID."""
        ...

    async def claim(self) -> Claim[T] | None:
        """Claim the next available entry, or return None if none is available."""
        ...

    async def heartbeat(self, claim: Claim[T]) -> bool:
        """Extend the claim's lease if it is still valid."""
        ...

    async def ack(self, claim: Claim[T]) -> None:
        """Acknowledge successful processing of a claimed entry."""
        ...

    async def retry(self, claim: Claim[T], *, delay: int) -> None:
        """Release a claimed entry for retry after the specified delay."""
        ...


# Agent

AgentWorkEntryType = Literal["decision", "response"]


@dataclass
class AgentWorkEntry[T]:
    id: str
    chat_id: str
    turn_id: str
    type: AgentWorkEntryType
    payload: T


type AgentWorkScheduler[T] = WorkScheduler[AgentWorkEntry[T]]
