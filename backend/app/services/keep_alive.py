"""
Lightweight Keep-Alive Background Service for Wind Forecast Decision Portal.

Periodically pings the backend health endpoint (every 10-14 minutes) to prevent
hosting platforms (such as Render free web services) from spinning down due to inactivity.

Key Design Elements:
- Overlap Prevention: Uses an asyncio.Lock and sequential sleep-after-request execution.
- Low Resource Footprint: Lightweight async GET request with 10s timeout.
- Safe Lifecycle: Integrated into FastAPI lifespan context manager for clean startup & shutdown.
- Resilience: Network, timeout, and DNS exceptions are caught and logged without terminating the server.
"""

import asyncio
import logging
from typing import Optional
import httpx

from app.config import settings

logger = logging.getLogger("keep_alive")


class KeepAliveService:
    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self._is_running = False

    @property
    def is_running(self) -> bool:
        """Return True if the background timer loop is currently active."""
        return self._is_running

    async def ping_once(self, url: Optional[str] = None) -> bool:
        """
        Execute a single health-check ping.
        Guarantees that overlapping pings cannot run concurrently.
        """
        target_url = url or settings.KEEP_ALIVE_URL

        if self._lock.locked():
            logger.warning("Keep-alive ping already in progress; skipping overlapping attempt.")
            return False

        async with self._lock:
            try:
                # 10s total timeout with 5s connect timeout prevents hung sockets
                timeout = httpx.Timeout(10.0, connect=5.0)
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.get(
                        target_url,
                        headers={"User-Agent": "GridBricks-KeepAlive/1.0"}
                    )
                    if response.status_code < 400:
                        logger.info("Keep-alive ping succeeded (HTTP %d): %s", response.status_code, target_url)
                        return True
                    else:
                        logger.warning("Keep-alive ping returned non-2xx status (HTTP %d): %s", response.status_code, target_url)
                        return False
            except Exception as exc:
                logger.warning("Keep-alive ping failed for %s: %s", target_url, exc)
                return False

    async def _run_loop(self):
        """Continuous background timer loop."""
        interval = max(60, settings.KEEP_ALIVE_INTERVAL_SECONDS)
        logger.info(
            "Keep-alive service active. Target: %s, Interval: %ds (%.1f minutes)",
            settings.KEEP_ALIVE_URL,
            interval,
            interval / 60.0
        )
        while self._is_running:
            try:
                await asyncio.sleep(interval)
                if not self._is_running:
                    break
                await self.ping_once()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Unexpected error in keep-alive loop: %s", exc, exc_info=True)

    def start(self):
        """Start the background keep-alive loop if not already running."""
        if not settings.KEEP_ALIVE_ENABLED:
            logger.info("Keep-alive service is disabled by configuration.")
            return

        if self._is_running:
            logger.debug("Keep-alive service is already running.")
            return

        self._is_running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Keep-alive background task started.")

    async def stop(self):
        """Stop and clean up the background keep-alive loop."""
        if not self._is_running and not self._task:
            return

        self._is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Keep-alive background task stopped.")


# Module-level singleton instance
keep_alive_service = KeepAliveService()
