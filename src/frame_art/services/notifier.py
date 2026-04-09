"""Push notification service via ntfy.sh."""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


class Notifier:
    """Send push notifications via ntfy.sh (or a self-hosted ntfy instance)."""

    def __init__(self, server: str, topic: str):
        self.url = f"{server.rstrip('/')}/{topic}"

    async def send(
        self,
        title: str,
        message: str,
        priority: int = 3,
        tags: list[str] | None = None,
    ) -> None:
        """Send a push notification. Failures are logged but not raised."""
        headers: dict[str, str] = {
            "Title": title,
            "Priority": str(priority),
        }
        if tags:
            headers["Tags"] = ",".join(tags)

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    self.url, content=message, headers=headers
                )
                resp.raise_for_status()
                logger.info("Notification sent: %s", title)
            except Exception as e:
                logger.warning("Failed to send notification: %s", e)


async def notify_success(
    notifier: Notifier, description: str, tv_name: str
) -> None:
    """Send a success notification."""
    await notifier.send(
        title="Frame TV Art Updated",
        message=f"'{description}' is now showing on {tv_name} TV",
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
