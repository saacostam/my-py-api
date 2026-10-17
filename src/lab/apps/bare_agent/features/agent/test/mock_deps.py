from unittest.mock import Mock

from lab.apps.bare_agent.features.agent.domain import (
    ChainOfThoughtRepository,
)


def mock_chain_of_thought_repository():
    return Mock(spec=ChainOfThoughtRepository)
