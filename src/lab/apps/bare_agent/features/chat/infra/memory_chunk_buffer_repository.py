from lab.apps.bare_agent.features.chat.domain import Chunk


class MemoryChunkBufferRepository:
    def __init__(self) -> None:
        self._chunks: list[Chunk] = []

    async def create(self, chunk: Chunk) -> Chunk:
        self._chunks.append(chunk)
        return chunk

    async def get_all_by_turn_ids(
        self,
        turn_ids: list[str],
    ) -> dict[str, list[Chunk]]:
        turn_ids_set = set(turn_ids)
        chunks_by_turn_id: dict[str, list[Chunk]] = {
            turn_id: [] for turn_id in turn_ids
        }

        for chunk in self._chunks:
            if chunk.turn_id in turn_ids_set:
                chunks_by_turn_id[chunk.turn_id].append(chunk)

        return chunks_by_turn_id

    async def remove(self, turn_id: str, index: int) -> None:
        self._chunks = [
            chunk
            for chunk in self._chunks
            if not (chunk.turn_id == turn_id and chunk.index == index)
        ]
