import asyncio
from contextlib import asynccontextmanager
from logging import getLogger

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from lab.apps.bare_agent.shared.di.infra import (
    agent_worker_use_cases,
    queue,
    run_agent_worker,
)
from lab.apps.bare_agent.shared.presentation import bare_agent_app_router
from lab.apps.todo.shared.presentation import todo_app_router
from lab.shared.errors.domain import DomainError
from lab.shared.errors.presentation import (
    domain_error_exception_handler,
    generic_exception_handler,
    validation_exception_handler,
)

logger = getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tasks
    worker_task = asyncio.create_task(
        run_agent_worker(
            queue=queue,
            agent_worker_use_cases=agent_worker_use_cases,
        ),
        name="bare-agent-worker",
    )

    try:
        yield
    finally:
        worker_task.cancel()
        await asyncio.gather(worker_task, return_exceptions=True)


app = FastAPI(lifespan=lifespan)

app.include_router(bare_agent_app_router, prefix="/bare-agent", tags=["bare-agent"])
app.include_router(todo_app_router, prefix="/todo", tags=["todo"])

app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(DomainError, domain_error_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"ok": True}
