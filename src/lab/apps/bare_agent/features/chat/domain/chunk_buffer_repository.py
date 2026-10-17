from typing import Protocol

from .chat import Chunk


class ChunkBufferRepository(Protocol):
    async def create(self, chunk: Chunk) -> Chunk: ...
    async def get_all_by_turn_ids(
        self, turn_ids: list[str]
    ) -> dict[str, list[Chunk]]: ...
    async def remove(self, turn_id: str, index: int) -> None: ...
