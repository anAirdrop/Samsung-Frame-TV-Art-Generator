"""Tests for the notification service."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from frame_art.services.notifier import (
    NotificationError,
    Notifier,
    notify_failure,
    notify_success,
)


@pytest.mark.asyncio
async def test_send_notification():
    notifier = Notifier(server="https://ntfy.sh", topic="test-topic")

    with patch("frame_art.services.notifier.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        await notifier.send(
            title="Test", message="Hello", priority=3, tags=["test"]
        )

        mock_client.post.assert_called_once()
        call_kwargs = mock_client.post.call_args
        assert call_kwargs[1]["content"] == "Hello" or call_kwargs[0][1] == "Hello"


@pytest.mark.asyncio
async def test_send_notification_failure_raises_actionable_error():
    notifier = Notifier(server="https://ntfy.sh", topic="test-topic")

    with patch("frame_art.services.notifier.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        request = httpx.Request("POST", "https://ntfy.sh/test-topic")
        mock_client.post.side_effect = httpx.ConnectError(
            "Network error", request=request
        )
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "frame_art.services.notifier.asyncio.sleep",
            new_callable=AsyncMock,
        ), pytest.raises(NotificationError, match="3 attempts"):
            await notifier.send(
                title="Test", message="Hello", priority=3, tags=None
            )


@pytest.mark.asyncio
async def test_notify_success():
    notifier = Notifier(server="https://ntfy.sh", topic="test")
    with patch.object(notifier, "send", new_callable=AsyncMock) as mock_send:
        await notify_success(notifier, "a sunset", "Living Room")
        mock_send.assert_called_once()
        assert "sunset" in mock_send.call_args[1]["message"]


@pytest.mark.asyncio
async def test_notify_failure():
    notifier = Notifier(server="https://ntfy.sh", topic="test")
    with patch.object(notifier, "send", new_callable=AsyncMock) as mock_send:
        await notify_failure(notifier, "TV unreachable")
        mock_send.assert_called_once()
        assert mock_send.call_args[1]["priority"] == 4
