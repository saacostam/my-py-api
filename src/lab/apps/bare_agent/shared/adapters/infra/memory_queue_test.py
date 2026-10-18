from datetime import timedelta

from lab.apps.bare_agent.shared.adapters.domain.queue import QueueEntry

from .memory_queue import InMemoryQueue


async def test_add_and_peek_returns_entry() -> None:
    queue = InMemoryQueue(timeout=timedelta(seconds=1))
    entry = QueueEntry(
        id="entry-1",
        chat_id="chat-1",
        cot_id="cot-1",
        type="decision",
        turn_id="turn-id",
    )

    result = await queue.add(entry)

    assert result == "entry-1"
    assert await queue.peek() == entry


async def test_peek_returns_none_when_queue_is_empty() -> None:
    queue = InMemoryQueue(timeout=timedelta(seconds=1))

    result = await queue.peek()

    assert result is None


async def test_peek_does_not_return_same_entry_before_timeout() -> None:
    queue = InMemoryQueue(timeout=timedelta(seconds=1))
    entry = QueueEntry(
        id="entry-1",
        chat_id="chat-1",
        cot_id="cot-1",
        type="decision",
        turn_id="turn-id",
    )

    await queue.add(entry)

    first_result = await queue.peek()
    second_result = await queue.peek()

    assert first_result == entry
    assert second_result is None


async def test_peek_returns_next_entry_when_first_entry_is_peeked() -> None:
    queue = InMemoryQueue(timeout=timedelta(seconds=1))

    first_entry = QueueEntry(
        id="entry-1",
        chat_id="chat-1",
        cot_id="cot-1",
        type="decision",
        turn_id="turn-id",
    )
    second_entry = QueueEntry(
        id="entry-2",
        chat_id="chat-2",
        cot_id="cot-2",
        type="decision",
        turn_id="turn-id",
    )

    await queue.add(first_entry)
    await queue.add(second_entry)

    first_result = await queue.peek()
    second_result = await queue.peek()

    assert first_result == first_entry
    assert second_result == second_entry


async def test_peek_returns_entry_again_after_timeout() -> None:
    queue = InMemoryQueue(timeout=timedelta(milliseconds=1))
    entry = QueueEntry(
        id="entry-1",
        chat_id="chat-1",
        cot_id="cot-1",
        type="decision",
        turn_id="turn-id",
    )

    await queue.add(entry)

    first_result = await queue.peek()

    await __import__("asyncio").sleep(0.002)

    second_result = await queue.peek()

    assert first_result == entry
    assert second_result == entry


async def test_remove_removes_entry_from_queue() -> None:
    queue = InMemoryQueue(timeout=timedelta(seconds=1))
    entry = QueueEntry(
        id="entry-1",
        chat_id="chat-1",
        cot_id="cot-1",
        type="decision",
        turn_id="turn-id",
    )

    await queue.add(entry)

    result = await queue.remove("entry-1")

    assert result == "entry-1"
    assert await queue.peek() is None


async def test_remove_allows_next_entry_to_be_peeked() -> None:
    queue = InMemoryQueue(timeout=timedelta(seconds=1))

    first_entry = QueueEntry(
        id="entry-1",
        chat_id="chat-1",
        cot_id="cot-1",
        type="decision",
        turn_id="turn-id",
    )
    second_entry = QueueEntry(
        id="entry-2",
        chat_id="chat-2",
        cot_id="cot-2",
        type="decision",
        turn_id="turn-id",
    )

    await queue.add(first_entry)
    await queue.add(second_entry)

    await queue.peek()
    await queue.remove("entry-1")

    result = await queue.peek()

    assert result == second_entry


async def test_remove_non_existent_entry_returns_null() -> None:
    queue = InMemoryQueue(timeout=timedelta(seconds=1))

    result = await queue.remove("non-existent-id")

    assert result is None
