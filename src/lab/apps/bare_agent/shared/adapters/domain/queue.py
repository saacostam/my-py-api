from dataclasses import dataclass
from typing import Literal, Protocol

QueueEntryType = Literal["decision", "response"]


@dataclass
class QueueEntry:
    id: str
    chat_id: str
    cot_id: str
    turn_id: str
    type: QueueEntryType


class Queue(Protocol):
    async def add(self, entry: QueueEntry) -> str: ...
    async def peek(self) -> QueueEntry | None: ...
    async def remove(self, id: str) -> str | None: ...
