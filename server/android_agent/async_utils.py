"""Bounded waits that preserve cancellation on Python 3.10 and later."""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import TypeVar

T = TypeVar("T")


async def wait_for(awaitable: Awaitable[T], timeout: float | None) -> T:
    # Older asyncio.wait_for can swallow caller cancellation when the child
    # completes concurrently. asyncio.wait preserves that cancellation.
    pending = asyncio.ensure_future(awaitable)
    try:
        done, _ = await asyncio.wait({pending}, timeout=timeout)
        if pending in done:
            return pending.result()
        raise asyncio.TimeoutError
    except BaseException:
        pending.cancel()
        await asyncio.gather(pending, return_exceptions=True)
        raise
