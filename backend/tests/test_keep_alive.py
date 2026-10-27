"""
Unit tests for the keep-alive background service, configuration, and overlap prevention.
"""

import asyncio
import os
from unittest.mock import patch, AsyncMock, MagicMock
import httpx
from fastapi.testclient import TestClient

from app.config import Settings
from app.services.keep_alive import KeepAliveService
from app.main import app


def test_config_keep_alive_defaults():
    """Verify default keep-alive settings when no environment variables are present."""
    with patch.dict(os.environ, {}, clear=True):
        custom_settings = Settings()
        assert custom_settings.KEEP_ALIVE_ENABLED is False
        assert custom_settings.KEEP_ALIVE_INTERVAL_SECONDS == 720
        assert custom_settings.KEEP_ALIVE_URL == "http://127.0.0.1:8000/api/health"


def test_config_keep_alive_render_auto_detection():
    """Verify automatic detection and URL derivation on Render environments."""
    # When RENDER_EXTERNAL_URL is provided by Render
    with patch.dict(os.environ, {"RENDER_EXTERNAL_URL": "https://custom-app.onrender.com"}, clear=True):
        custom_settings = Settings()
        assert custom_settings.KEEP_ALIVE_ENABLED is True
        assert custom_settings.KEEP_ALIVE_URL == "https://custom-app.onrender.com/api/health"

    # When explicit KEEP_ALIVE_URL is provided
    with patch.dict(os.environ, {"KEEP_ALIVE_URL": "https://my-backend.example.com/api/health"}, clear=True):
        custom_settings = Settings()
        assert custom_settings.KEEP_ALIVE_ENABLED is True
        assert custom_settings.KEEP_ALIVE_URL == "https://my-backend.example.com/api/health"

    # When explicit KEEP_ALIVE_ENABLED='false' overrides detection
    with patch.dict(os.environ, {"RENDER": "true", "KEEP_ALIVE_ENABLED": "false"}, clear=True):
        custom_settings = Settings()
        assert custom_settings.KEEP_ALIVE_ENABLED is False


def test_ping_once_success():
    """Verify successful health check ping returns True."""
    async def _run():
        service = KeepAliveService()
        mock_response = MagicMock(status_code=200)
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            result = await service.ping_once("http://testservice/api/health")
            assert result is True
            mock_get.assert_called_once()
            args, kwargs = mock_get.call_args
            assert args[0] == "http://testservice/api/health"
            assert kwargs["headers"]["User-Agent"] == "GridBricks-KeepAlive/1.0"

    asyncio.run(_run())


def test_ping_once_http_error():
    """Verify HTTP error status returns False without raising exception."""
    async def _run():
        service = KeepAliveService()
        mock_response = MagicMock(status_code=503)
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            result = await service.ping_once("http://testservice/api/health")
            assert result is False

    asyncio.run(_run())


def test_ping_once_network_exception():
    """Verify network exceptions are caught gracefully and return False."""
    async def _run():
        service = KeepAliveService()
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.ConnectError("Connection refused")
            result = await service.ping_once("http://unreachable/api/health")
            assert result is False

    asyncio.run(_run())


def test_overlap_prevention():
    """Verify that while a ping is in-flight, an overlapping ping call is rejected."""
    async def _run():
        service = KeepAliveService()
        gate = asyncio.Event()

        async def slow_get(*args, **kwargs):
            await gate.wait()
            return MagicMock(status_code=200)

        with patch("httpx.AsyncClient.get", side_effect=slow_get):
            # Start first ping task
            first_task = asyncio.create_task(service.ping_once("http://slow/api/health"))
            # Yield control so first task enters the lock
            await asyncio.sleep(0.01)

            # Attempt overlapping ping while first is still waiting on gate
            overlapping_result = await service.ping_once("http://slow/api/health")
            assert overlapping_result is False

            # Release the first task
            gate.set()
            first_result = await first_task
            assert first_result is True

    asyncio.run(_run())


def test_service_start_and_stop():
    """Verify service start and stop lifecycle methods."""
    async def _run():
        service = KeepAliveService()

        with patch.dict(os.environ, {"KEEP_ALIVE_ENABLED": "true", "KEEP_ALIVE_INTERVAL_SECONDS": "1"}):
            service.start()
            assert service.is_running is True
            task = service._task
            assert task is not None and not task.done()

            # Calling start again should not re-spawn
            service.start()
            assert service._task is task

            # Stop service
            await service.stop()
            assert service.is_running is False
            assert service._task is None
            assert task.cancelled() or task.done()

    asyncio.run(_run())


def test_fastapi_lifespan_integration():
    """Verify FastAPI lifespan executes cleanly with TestClient."""
    with TestClient(app) as client:
        res = client.get("/api/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"
