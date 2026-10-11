"""
Utilities for handling async/sync boundaries.

Provides helpers for running async code in sync contexts and vice versa,
with proper event loop handling to avoid nested loop issues.
"""

import asyncio
from typing import Any, Coroutine, TypeVar
from functools import wraps
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class AsyncSync:
    """Utilities for bridging async and sync code."""

    @staticmethod
    def run_sync(coro: Coroutine[Any, Any, T]) -> T:
        """
        Run a coroutine synchronously.

        Handles nested event loops by using nest_asyncio if needed.

        Args:
            coro: Coroutine to run

        Returns:
            Result of the coroutine

        Raises:
            RuntimeError: If event loop handling fails
        """
        try:
            # Try to get running loop
            loop = asyncio.get_running_loop()

            # If we're already in an async context, we need nest_asyncio
            try:
                import nest_asyncio
                nest_asyncio.apply()
                return asyncio.run(coro)
            except ImportError:
                logger.warning(
                    "nest_asyncio not available. "
                    "Install with: pip install nest-asyncio"
                )
                raise RuntimeError(
                    "Cannot run async code in sync context without nest_asyncio"
                )

        except RuntimeError:
            # No running loop, we can safely use asyncio.run()
            return asyncio.run(coro)

    @staticmethod
    async def run_async(func: callable, *args, **kwargs) -> Any:
        """
        Run a synchronous function in async context using executor.

        Args:
            func: Synchronous function to run
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Result of the function
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: func(*args, **kwargs)
        )

    @staticmethod
    def make_sync(async_func: callable) -> callable:
        """
        Decorator to make an async function callable synchronously.

        Args:
            async_func: Async function to wrap

        Returns:
            Synchronous wrapper function

        Example:
            @make_sync
            async def async_function():
                return await some_async_operation()

            # Can now call synchronously
            result = async_function()
        """
        @wraps(async_func)
        def wrapper(*args, **kwargs):
            coro = async_func(*args, **kwargs)
            return AsyncSync.run_sync(coro)
        return wrapper

    @staticmethod
    def make_async(sync_func: callable) -> callable:
        """
        Decorator to make a sync function callable asynchronously.

        Args:
            sync_func: Synchronous function to wrap

        Returns:
            Async wrapper function

        Example:
            @make_async
            def sync_function():
                return some_blocking_operation()

            # Can now await
            result = await sync_function()
        """
        @wraps(sync_func)
        async def wrapper(*args, **kwargs):
            return await AsyncSync.run_async(sync_func, *args, **kwargs)
        return wrapper


def ensure_event_loop():
    """
    Ensure an event loop exists for the current thread.

    Creates a new event loop if one doesn't exist.
    """
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
