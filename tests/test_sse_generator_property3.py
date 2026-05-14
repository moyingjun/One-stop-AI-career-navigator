"""
Property-Based Test — Property 3: SSE stream always terminates with done event

Validates: Requirements 6.6, 6.7, 6.8

Tests that stream_interview_response always yields 'event: done\ndata: {}\n\n'
as its final item, regardless of whether the HTTP call succeeds, times out,
or raises a generic exception.
"""

import sys
import os

# Ensure the project root is on the path so Router.interview can be imported
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from Router.interview import stream_interview_response, ChatRequest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def collect_events(request: ChatRequest) -> list[str]:
    """Drain the async generator and return all yielded strings."""
    events = []
    async for chunk in stream_interview_response(request):
        events.append(chunk)
    return events


def make_request() -> ChatRequest:
    """Return a minimal ChatRequest suitable for all test cases."""
    return ChatRequest(
        user_query="Tell me about yourself.",
        history=[],
        resume_text="",
        jd_text="",
        difficulty="standard",
    )


# ---------------------------------------------------------------------------
# Async line iterator helper
# ---------------------------------------------------------------------------

class AsyncLineIterator:
    """Async iterator that yields lines from a list, simulating aiter_lines()."""

    def __init__(self, lines: list[str]):
        self._lines = iter(lines)

    def __aiter__(self):
        return self

    async def __anext__(self) -> str:
        try:
            return next(self._lines)
        except StopIteration:
            raise StopAsyncIteration


# ---------------------------------------------------------------------------
# Test 1 — Success case
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_stream_terminates_with_done_on_success():
    """
    Property 3 — success path:
    When the HTTP stream returns valid SSE data lines followed by [DONE],
    the last yielded item must be 'event: done\\ndata: {}\\n\\n'.

    Validates: Requirements 6.6, 6.7, 6.8
    """
    # Build realistic SSE lines that DeepSeek would return
    def make_data_line(content: str) -> str:
        payload = json.dumps(
            {"choices": [{"delta": {"content": content}}]},
            ensure_ascii=False,
        )
        return f"data: {payload}"

    sse_lines = [
        make_data_line("Hello"),
        make_data_line(", how"),
        make_data_line(" are you?"),
        "data: [DONE]",
    ]

    # Build the mock response context manager
    mock_response = MagicMock()
    mock_response.aiter_lines = MagicMock(return_value=AsyncLineIterator(sse_lines))
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)

    # Build the mock client context manager
    mock_client = MagicMock()
    mock_client.stream = MagicMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("Router.interview.httpx.AsyncClient", return_value=mock_client):
        events = await collect_events(make_request())

    assert len(events) > 0, "Generator must yield at least one event"
    assert events[-1] == "event: done\ndata: {}\n\n", (
        f"Last event must be the done sentinel, got: {events[-1]!r}"
    )


# ---------------------------------------------------------------------------
# Test 2 — Timeout case
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_stream_terminates_with_done_on_timeout():
    """
    Property 3 — timeout path:
    When httpx.AsyncClient raises httpx.ReadTimeout, the generator must still
    yield 'event: done\\ndata: {}\\n\\n' as its final item.

    Validates: Requirements 6.6, 6.7, 6.8
    """
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(side_effect=httpx.ReadTimeout("timed out"))
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("Router.interview.httpx.AsyncClient", return_value=mock_client):
        events = await collect_events(make_request())

    assert len(events) > 0, "Generator must yield at least one event"
    assert events[-1] == "event: done\ndata: {}\n\n", (
        f"Last event must be the done sentinel after timeout, got: {events[-1]!r}"
    )


# ---------------------------------------------------------------------------
# Test 3 — Generic exception case
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_stream_terminates_with_done_on_generic_exception():
    """
    Property 3 — generic exception path:
    When httpx.AsyncClient raises an unexpected Exception, the generator must
    still yield 'event: done\\ndata: {}\\n\\n' as its final item.

    Validates: Requirements 6.6, 6.7, 6.8
    """
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(side_effect=Exception("unexpected error"))
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("Router.interview.httpx.AsyncClient", return_value=mock_client):
        events = await collect_events(make_request())

    assert len(events) > 0, "Generator must yield at least one event"
    assert events[-1] == "event: done\ndata: {}\n\n", (
        f"Last event must be the done sentinel after generic exception, got: {events[-1]!r}"
    )
