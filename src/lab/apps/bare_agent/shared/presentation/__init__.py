from fastapi import APIRouter

from lab.apps.bare_agent.features.agent.presentation import agent_router
from lab.apps.bare_agent.features.user.presentation import user_router

bare_agent_app_router = APIRouter()

bare_agent_app_router.include_router(agent_router, prefix="/agent", tags=["agent"])
bare_agent_app_router.include_router(user_router, prefix="/user", tags=["user"])
