from lab.apps.bare_agent.features.chat.domain import (
    Chat,
    Chunk,
    Turn,
    TurnStatus,
    TurnType,
)

id = 0


def _getId() -> str:
    global id
    id += 1
    return str(id)


def seed_chat(
    id: str | None = None,
    user_id: str | None = None,
    turns: list[Turn] | None = None,
) -> Chat:
    return Chat(
        id=id if id else _getId(),
        user_id=user_id if user_id else _getId(),
        turns=turns if turns else [],
    )


def seed_chunk(
    index: int | None = None,
    turn_id: str | None = None,
    content: str | None = None,
) -> Chunk:
    return Chunk(
        index=index if index else id,
        turn_id=turn_id if turn_id else _getId(),
        content=content if content else _getId(),
    )


def seed_turn(
    id: str | None = None,
    type: TurnType | None = None,
    status: TurnStatus | None = None,
    content: str | None = None,
) -> Turn:
    return Turn(
        id=id if id else _getId(),
        type=type if type else TurnType.ASSISTANT,
        status=status if status else TurnStatus.SUCCESS,
        content=content if content else _getId(),
    )
