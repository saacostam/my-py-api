from pydantic import BaseModel

from lab.apps.bare_agent.features.chat.domain import TurnType


class CreateAgentRequest(BaseModel):
    message: str


class ChatIdentifierResponse(BaseModel):
    chat_id: str


class TurnResponse(BaseModel):
    id: str
    type: TurnType
    content: str


class GetAgentResponse(BaseModel):
    id: str
    user_id: str
    turns: list[TurnResponse]


class LeanChatResponse(BaseModel):
    id: str
    user_id: str
