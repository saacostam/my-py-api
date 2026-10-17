from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum
from typing import Protocol, TypeVar

from pydantic import BaseModel


class MessageRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class Message:
    role: MessageRole
    content: str


OutputT = TypeVar("OutputT", bound=BaseModel)


class LLMProvider(Protocol):
    async def generate(
        self,
        messages: list[Message],
        output_schema: type[OutputT],
    ) -> OutputT: ...

    async def stream(
        self,
        messages: list[Message],
        onCreated: Callable[[], Awaitable[None]],
        onMessage: Callable[[str, int], Awaitable[None]],
        onCompleted: Callable[[], Awaitable[None]],
        onError: Callable[[str], Awaitable[None]],
    ) -> None: ...
