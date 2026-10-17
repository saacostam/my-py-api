from lab.apps.bare_agent.features.chat.domain import Chunk


class MemoryChunkBufferRepository:
    def __init__(self) -> None:
        self._chunks: list[Chunk] = []

    async def create(self, chunk: Chunk) -> Chunk:
        self._chunks.append(chunk)
        return chunk

    async def get_all_by_turn_id(self, turn_id: str) -> list[Chunk]:
        chunks: list[Chunk] = []

        for chunk in self._chunks:
            if chunk.turn_id == turn_id:
                chunks.append(chunk)

        return chunks

    async def remove(self, turn_id: str, index: int) -> None:
        self._chunks = [
            chunk
            for chunk in self._chunks
            if (chunk.turn_id == turn_id and chunk.index == index)
        ]
