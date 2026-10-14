import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import asdict

from lab.apps.bare_agent.shared.adapters.domain import (
    EventEmitterPayload,
)


class UserSSEEventEmitter:
    HEARTBEAT_INTERVAL_SECONDS = 15

    def __init__(self) -> None:
        self._connections: dict[
            str,
            set[asyncio.Queue[EventEmitterPayload]],
        ] = {}
        self._lock = asyncio.Lock()

    async def send(
        self,
        id: str,
        event: EventEmitterPayload,
    ) -> None:
        async with self._lock:
            queues = list(self._connections.get(id, set()))

        for queue in queues:
            await queue.put(event)

    async def subscribe(self, id: str) -> AsyncIterator[str]:
        queue: asyncio.Queue[EventEmitterPayload] = asyncio.Queue()

        async with self._lock:
            self._connections.setdefault(id, set()).add(queue)

        try:
            while True:
                try:
                    event = await asyncio.wait_for(
                        queue.get(),
                        timeout=self.HEARTBEAT_INTERVAL_SECONDS,
                    )
                except TimeoutError:
                    yield ": keep-alive\n\n"
                    continue

                data = json.dumps(
                    {
                        "type": event.type,
                        "data": {
                            key: value
                            for key, value in asdict(event).items()
                            if key != "type"
                        },
                    }
                )
                yield f"data: {data}\n\n"
        finally:
            async with self._lock:
                queues = self._connections.get(id)

                if queues is not None:
                    queues.discard(queue)

                    if not queues:
                        del self._connections[id]
