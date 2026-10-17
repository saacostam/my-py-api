from dataclasses import dataclass
from enum import Enum


@dataclass
class Chunk:
    index: int
    turn_id: str
    content: str


class TurnType(Enum):
    ASSISTANT = "ASSISTANT"
    USER = "USER"


class TurnStatus(Enum):
    ERROR = "ERROR"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"


@dataclass
class Turn:
    id: str
    type: TurnType
    content: str
    status: TurnStatus


@dataclass
class LeanChat:
    id: str
    user_id: str


@dataclass
class Chat(LeanChat):
    turns: list[Turn]
