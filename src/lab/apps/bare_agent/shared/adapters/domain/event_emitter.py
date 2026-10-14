from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True)
class EventCreated:
    turn_id: str
    type: Literal["created"] = "created"


@dataclass(frozen=True)
class EventMessage:
    content: str
    turn_id: str
    type: Literal["message"] = "message"


@dataclass(frozen=True)
class EventCompleted:
    turn_id: str
    type: Literal["completed"] = "completed"


@dataclass(frozen=True)
class EventError:
    message: str
    turn_id: str
    type: Literal["error"] = "error"


type EventEmitterPayload = EventCreated | EventMessage | EventCompleted | EventError


class EventEmitter(Protocol):
    async def send(
        self,
        id: str,
        event: EventEmitterPayload,
    ) -> None: ...
