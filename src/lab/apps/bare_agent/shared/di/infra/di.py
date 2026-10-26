from dotenv import load_dotenv

load_dotenv()

from datetime import timedelta
from logging import getLogger

from openai import AsyncOpenAI

from lab.apps.bare_agent.features.agent.app import (
    AgentUseCases,
    AgentWorkerUseCases,
)
from lab.apps.bare_agent.features.agent.domain import (
    ChainOfThoughtRepository,
)
from lab.apps.bare_agent.features.agent.infra import (
    MemoryThoughtRepository,
)
from lab.apps.bare_agent.features.auth.app import (
    AuthUseCases,
)
from lab.apps.bare_agent.features.chat.domain import (
    ChatRepository,
    ChunkBufferRepository,
)
from lab.apps.bare_agent.features.chat.infra import (
    MemoryChatRepository,
    MemoryChunkBufferRepository,
)
from lab.apps.bare_agent.features.user.app import (
    UserUseCases,
)
from lab.apps.bare_agent.features.user.domain import (
    UserRepository,
)
from lab.apps.bare_agent.features.user.infra import (
    MemoryUserRepository,
)
from lab.apps.bare_agent.shared.adapters.domain import (
    IdGenerator,
    JwtAdapter,
    LLMProvider,
    Logger,
    PasswordHasher,
    Queue,
)
from lab.apps.bare_agent.shared.adapters.infra import (
    BcryptPasswordHasher,
    InMemoryQueue,
    OpenAiLLMProvider,
    PyJwtAdapter,
    PythonLogger,
    UserSSEEventEmitter,
    UuidGenerator,
)
from lab.apps.bare_agent.shared.dependencies import AuthDependency

# Shared
user_sse_event_emitter = UserSSEEventEmitter()
id_generator: IdGenerator = UuidGenerator()
jwt_adapter: JwtAdapter = PyJwtAdapter()
llm_provider: LLMProvider = OpenAiLLMProvider(
    client=AsyncOpenAI(),
)
logger: Logger = PythonLogger(logger=getLogger(name="Logger"))
queue: Queue = InMemoryQueue(timeout=timedelta(minutes=5))
password_hasher: PasswordHasher = BcryptPasswordHasher()

# Auth Module
auth_use_cases = AuthUseCases(
    jwt=jwt_adapter,
)

# Chat Module
chat_repo: ChatRepository = MemoryChatRepository()
chunk_buffer_repository: ChunkBufferRepository = MemoryChunkBufferRepository()

# Agent Module
cot_repo: ChainOfThoughtRepository = MemoryThoughtRepository()
agent_use_cases = AgentUseCases(
    chat_repo=chat_repo,
    chunk_buffer_repo=chunk_buffer_repository,
    cot_repo=cot_repo,
    id_generator=id_generator,
    queue=queue,
)
agent_worker_use_cases = AgentWorkerUseCases(
    chat_repo=chat_repo,
    chunk_buffer_repo=chunk_buffer_repository,
    cot_repo=cot_repo,
    id_generator=id_generator,
    llm=llm_provider,
    logger=logger,
    queue=queue,
    user_event_emitter=user_sse_event_emitter,
)

# User Module
user_repo: UserRepository = MemoryUserRepository()
user_use_cases = UserUseCases(
    jwt_adapter=jwt_adapter,
    id_generator=id_generator,
    password_hasher=password_hasher,
    user_repo=user_repo,
)

# Deps
get_current_user = AuthDependency(
    auth_use_cases=auth_use_cases,
)
