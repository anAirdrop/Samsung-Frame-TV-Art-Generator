"""Push notification service via ntfy.sh."""

from __future__ import annotations

import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)
_MAX_ATTEMPTS = 3


class NotificationError(RuntimeError):
    """Raised when an optional notification cannot be delivered."""


class Notifier:
    """Send push notifications via ntfy.sh (or a self-hosted ntfy instance)."""

    def __init__(self, server: str, topic: str):
        self.server = server.rstrip("/")
        self.url = f"{server.rstrip('/')}/{topic}"

    async def send(
        self,
        title: str,
        message: str,
        priority: int,
        tags: list[str] | None,
    ) -> None:
        """Send a push notification with bounded retries."""
        headers: dict[str, str] = {
            "Title": title,
            "Priority": str(priority),
        }
        if tags:
            headers["Tags"] = ",".join(tags)

        last_error: httpx.HTTPError | None = None
        async with httpx.AsyncClient(timeout=10.0) as client:
            for attempt in range(1, _MAX_ATTEMPTS + 1):
                try:
                    response = await client.post(
                        self.url, content=message, headers=headers
                    )
                    response.raise_for_status()
                    return
                except httpx.HTTPError as error:
                    last_error = error
                    logger.warning(
                        "Notification delivery failed",
                        extra={
                            "attempt": attempt,
                            "server": self.server,
                            "error_type": type(error).__name__,
                            "status_code": (
                                error.response.status_code
                                if isinstance(error, httpx.HTTPStatusError)
                                else None
                            ),
                        },
                    )
                    if attempt < _MAX_ATTEMPTS:
                        await asyncio.sleep(2 ** (attempt - 1))

        if last_error is None:
            raise NotificationError(
                "Notification delivery failed without an HTTP error: "
                f"server={self.server}"
            )
        raise NotificationError(
            f"Notification delivery failed after {_MAX_ATTEMPTS} attempts: "
            f"server={self.server}, error_type={type(last_error).__name__}"
        ) from last_error


async def notify_success(
    notifier: Notifier, description: str, tv_name: str
) -> None:
    """Send a success notification."""
    await notifier.send(
        title="Frame TV Art Updated",
        message=f"'{description}' is now showing on {tv_name} TV",
        priority=3,
        tags=["art", "framed_picture"],
    )


async def notify_failure(notifier: Notifier, error: str) -> None:
    """Send a failure notification."""
    await notifier.send(
        title="Frame TV Art Failed",
        message=f"Error: {error}",
        priority=4,
        tags=["warning"],
    )
