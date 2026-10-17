from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from lab.apps.bare_agent.features.chat.domain import (
    Chunk,
    TurnStatus,
    TurnType,
)


@dataclass
class ErrorTurn:
    id: str
    type: TurnType
    status: Literal[TurnStatus.ERROR]
    content: str


@dataclass
class SuccessTurn:
    id: str
    type: TurnType
    status: Literal[TurnStatus.SUCCESS]
    content: str


@dataclass
class ProcessingTurn:
    id: str
    type: TurnType
    status: Literal[TurnStatus.PROCESSING]
    chunks: list[Chunk]


type ChatTurn = ErrorTurn | SuccessTurn | ProcessingTurn


@dataclass
class ChatDetails:
    id: str
    user_id: str
    turns: Sequence[ChatTurn]
