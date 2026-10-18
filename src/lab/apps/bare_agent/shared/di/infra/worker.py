import asyncio
from logging import getLogger

from lab.apps.bare_agent.features.agent.app import AgentWorkerUseCases
from lab.apps.bare_agent.shared.adapters.domain import Queue

logger = getLogger(__name__)


async def run_agent_worker(
    queue: Queue,
    agent_worker_use_cases: AgentWorkerUseCases,
    poll_interval: float = 0.1,
) -> None:
    logger.info("Agent worker started")

    while True:
        entry = await queue.peek()

        if entry is None:
            await asyncio.sleep(poll_interval)
            continue

        try:
            if entry.type == "decision":
                await agent_worker_use_cases.decision(
                    chat_id=entry.chat_id,
                    cot_id=entry.cot_id,
                    turn_id=entry.turn_id,
                )
            elif entry.type == "response":
                await agent_worker_use_cases.response(
                    chat_id=entry.chat_id,
                    cot_id=entry.cot_id,
                    turn_id=entry.turn_id,
                )
            else:
                raise ValueError(f"Unsupported queue entry type: {entry.type}")

            await queue.remove(id=entry.id)

        except asyncio.CancelledError:
            raise

        except Exception:
            logger.exception(
                "Failed to process queue entry %s; leaving it queued for retry",
                entry.id,
            )
