from unittest.mock import Mock

from lab.apps.bare_agent.features.agent.app import (
    AgentUseCases,
    AgentWorkerUseCases,
)
from lab.apps.bare_agent.features.agent.domain import (
    ChainOfThoughtRepository,
)


def mock_chain_of_thought_repository():
    return Mock(spec=ChainOfThoughtRepository)


def mock_agent_use_cases():
    return Mock(spec=AgentUseCases)


def mock_agent_worker_use_cases():
    return Mock(spec=AgentWorkerUseCases)
