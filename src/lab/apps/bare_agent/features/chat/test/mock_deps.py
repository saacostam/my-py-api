from unittest.mock import Mock

from lab.apps.bare_agent.features.chat.domain import (
    ChatRepository,
    ChunkBufferRepository,
)


def mock_chat_repository():
    return Mock(spec=ChatRepository)


def mock_chunk_buffer_repository():
    return Mock(spec=ChunkBufferRepository)
