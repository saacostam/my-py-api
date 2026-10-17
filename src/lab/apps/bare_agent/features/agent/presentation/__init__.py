from collections.abc import AsyncIterator
from typing import Annotated, Protocol

from fastapi import APIRouter, Path, Query
from fastapi.responses import StreamingResponse

from lab.apps.bare_agent.features.chat.domain import LeanChat
from lab.apps.bare_agent.shared.di.infra import (
    agent_use_cases,
    user_sse_event_emitter,
)

from .schema import (
    ChatIdentifierResponse,
    CreateAgentRequest,
    LeanChatResponse,
)

agent_router = APIRouter()


class EventSubscriber(Protocol):
    def subscribe(self, id: str) -> AsyncIterator[str]: ...


@agent_router.post("/", response_model=ChatIdentifierResponse)
async def create_agent(
    request: CreateAgentRequest,
) -> ChatIdentifierResponse:
    result = await agent_use_cases.create(message=request.message)

    return ChatIdentifierResponse(chat_id=result.chat_id)


@agent_router.post("/{chat_id}/resume", response_model=ChatIdentifierResponse)
async def resume_agent(
    chat_id: Annotated[str, Path()],
    request: CreateAgentRequest,
) -> ChatIdentifierResponse:
    result = await agent_use_cases.resume(
        chat_id=chat_id,
        message=request.message,
    )

    return ChatIdentifierResponse(chat_id=result.chat_id)


@agent_router.get("/", response_model=list[LeanChatResponse])
async def get_all_chats() -> list[LeanChatResponse]:
    chats: list[LeanChat] = await agent_use_cases.get_all_chats()

    return [
        LeanChatResponse(
            id=chat.id,
            user_id=chat.user_id,
        )
        for chat in chats
    ]


@agent_router.get("/id/{chat_id}")
async def get_agent(
    chat_id: Annotated[str, Path()],
):
    chat = await agent_use_cases.get_by_id(chat_id=chat_id)

    return chat


@agent_router.get("/events")
async def get_agent_events(
    user_id: Annotated[str, Query()] = "public",
) -> StreamingResponse:
    subscriber: EventSubscriber = user_sse_event_emitter

    return StreamingResponse(
        subscriber.subscribe(user_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
