from pydantic import BaseModel


class CreateAgentRequest(BaseModel):
    message: str


class ChatIdentifierResponse(BaseModel):
    chat_id: str


class LeanChatResponse(BaseModel):
    id: str
    user_id: str
