from collections.abc import Awaitable, Callable

from lab.apps.bare_agent.features.agent.app import AgentWorkerUseCases
from lab.apps.bare_agent.shared.adapters.domain import (
    AgentWorkScheduler,
    Logger,
)


class WorkerProcessUseCase:
    def __init__(
        self,
        scheduler: AgentWorkScheduler,
        agent_worker_use_cases: AgentWorkerUseCases,
        logger: Logger,
        sleep: Callable[[float], Awaitable[None]],
        poll_interval: float = 0.1,
        retry_delay: int = 1,
    ) -> None:
        self.scheduler = scheduler
        self.agent_worker_use_cases = agent_worker_use_cases
        self.logger = logger
        self.sleep = sleep
        self.poll_interval = poll_interval
        self.retry_delay = retry_delay

    async def run(self) -> None:
        while True:
            claim = await self.scheduler.claim()

            if claim is None:
                await self.sleep(self.poll_interval)
                continue

            entry = claim.entry

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
                    raise ValueError(f"Unsupported work entry type: {entry.type}")

                await self.scheduler.ack(claim)
            except BaseException:  # noqa: BLE001
                self.logger.error(
                    f"Failed to process work entry {entry.id}; scheduling it for retry"
                )
                await self.scheduler.retry(
                    claim,
                    delay=self.retry_delay,
                )
