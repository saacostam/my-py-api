from collections.abc import Awaitable, Callable

from openai import AsyncOpenAI

from lab.apps.bare_agent.shared.adapters.domain import (
    LLMProvider,
    Message,
    OutputT,
)


class OpenAiLLMProvider(LLMProvider):
    def __init__(self, client: AsyncOpenAI, model: str = "gpt-6-luna") -> None:
        self._client = client
        self._model = model

    async def generate(
        self,
        messages: list[Message],
        output_schema: type[OutputT],
    ) -> OutputT:
        response = await self._client.responses.parse(
            model=self._model,
            input=[
                {
                    "role": message.role.value,
                    "content": message.content,
                }
                for message in messages
            ],
            text_format=output_schema,
        )

        result = response.output_parsed

        if result is None:
            raise ValueError("OpenAI did not return a structured output.")

        return result

    async def stream(
        self,
        messages: list[Message],
        onCreated: Callable[[], Awaitable[None]],
        onMessage: Callable[[str, int], Awaitable[None]],
        onCompleted: Callable[[], Awaitable[None]],
        onError: Callable[[str], Awaitable[None]],
    ) -> None:
        stream = await self._client.responses.create(
            model=self._model,
            input=[
                {
                    "role": message.role.value,
                    "content": message.content,
                }
                for message in messages
            ],
            stream=True,
        )

        index = 0
        async for event in stream:
            if event.type == "response.created":
                await onCreated()
            elif event.type == "response.output_text.delta":
                await onMessage(event.delta, index)
                index += 1
            elif event.type == "error":
                message = event.message
                await onError(message)
                raise RuntimeError(f"OpenAI stream failed: {message}")

            elif event.type == "response.failed":
                message = str(event.response)
                await onError(message)
                raise RuntimeError(f"OpenAI response failed: {message}")
            elif event.type == "response.completed":
                await onCompleted()
