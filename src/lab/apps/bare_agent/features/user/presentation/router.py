from fastapi import APIRouter, Depends
from pydantic import BaseModel

from lab.apps.todo.shared.adapters.domain import TokenPayload
from lab.apps.todo.shared.di.infra import get_current_user, user_use_cases

user_router = APIRouter()


class CreateUserRequest(BaseModel):
    name: str
    password: str


@user_router.post("/")
async def signup_user_route(request: CreateUserRequest) -> str:
    res = await user_use_cases.signup(name=request.name, password=request.password)
    return res


class LoginRequest(BaseModel):
    name: str
    password: str


@user_router.post("/login")
async def login_user_router(request: LoginRequest) -> str:
    res = await user_use_cases.login(name=request.name, password=request.password)
    return res


@user_router.get("/me")
async def get_current_user_route(payload: TokenPayload = Depends(get_current_user)):
    user_id = payload.user_id
    return await user_use_cases.get_by_id(id=user_id)
