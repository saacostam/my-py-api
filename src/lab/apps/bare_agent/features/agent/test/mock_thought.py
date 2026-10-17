from lab.apps.bare_agent.features.agent.domain.though import (
    ChainOfThought,
    Thought,
)

id = 0


def _getId() -> str:
    global id
    id += 1
    return str(id)


def mock_thought(
    id: str | None = None,
    content: str | None = None,
) -> Thought:
    return Thought(
        id=id if id else _getId(),
        content=content if content else _getId(),
    )


def mock_chain_of_thought(
    id: str | None = None,
    chat_id: str | None = None,
    objective: str | None = None,
    thoughts: list[Thought] | None = None,
) -> ChainOfThought:
    return ChainOfThought(
        id=id if id else _getId(),
        chat_id=chat_id if chat_id else _getId(),
        objective=objective if objective else _getId(),
        thoughts=thoughts if thoughts else [],
    )
