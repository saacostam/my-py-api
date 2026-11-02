from collections.abc import Awaitable, Callable

from lab.apps.bare_agent.features.agent.app import AgentWorkerUseCases
from lab.apps.bare_agent.shared.adapters.domain import Logger, Queue


class WorkerProcessUseCase:
    def __init__(
        self,
        queue: Queue,
        agent_worker_use_cases: AgentWorkerUseCases,
        logger: Logger,
        sleep: Callable[[float], Awaitable[None]],
        poll_interval: float = 0.1,
    ):
        self.queue = queue
        self.agent_worker_use_cases = agent_worker_use_cases
        self.poll_interval = poll_interval
        self.sleep = sleep
        self.logger = logger

    async def run(self) -> None:
        while True:
            entry = await self.queue.peek()
            if entry is None:
                await self.sleep(self.poll_interval)
                continue

            try:
                if entry.type == "decision":
                    await self.agent_worker_use_cases.decision(
                        chat_id=entry.chat_id,
                        cot_id=entry.cot_id,
                        turn_id=entry.turn_id,
                    )
                elif entry.type == "response":
                    await self.agent_worker_use_cases.response(
                        chat_id=entry.chat_id,
                        cot_id=entry.cot_id,
                        turn_id=entry.turn_id,
                    )
                else:
                    raise ValueError(f"Unsupported queue entry type: {entry.type}")

                await self.queue.remove(id=entry.id)
            except BaseException:  # noqa: BLE001
                self.logger.error(
                    f"Failed to process queue entry {entry.id}; "
                    "leaving it queued for retry"
                )
