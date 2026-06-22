import asyncio
import sys
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


def run_in_playwright_loop(factory: Callable[[], Awaitable[T]]) -> T:
    """
    Run Playwright coroutines on a Windows-compatible event loop.

    Uvicorn's default loop on Windows cannot spawn Playwright subprocesses.
    """

    async def runner() -> T:
        return await factory()

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    return asyncio.run(runner())


async def run_playwright_task(factory: Callable[[], Awaitable[T]]) -> T:
    return await asyncio.to_thread(run_in_playwright_loop, factory)
