"""Samsung Frame TV controller — upload art and set it as active display."""

from __future__ import annotations

import logging
from pathlib import Path

from ..config import TVConfig

logger = logging.getLogger(__name__)


class TVController:
    """Manages communication with a single Samsung Frame TV."""

    def __init__(self, tv_config: TVConfig):
        self.host = tv_config.host
        self.port = tv_config.port
        self.token_file = tv_config.token_file
        self.matte = tv_config.matte

    def _ensure_token_dir(self) -> None:
        if self.token_file:
            Path(self.token_file).parent.mkdir(parents=True, exist_ok=True)

    def _connect(self):
        from samsungtvws import SamsungTVWS

        self._ensure_token_dir()
        return SamsungTVWS(
            host=self.host,
            port=self.port,
            token_file=self.token_file or None,
        )

    def upload_and_display(
        self, image_data: bytes, file_type: str = "JPEG"
    ) -> str:
        """Upload an image to the TV and set it as the active art.

        Returns the content_id of the uploaded image.
        """
        tv = self._connect()
        try:
            art = tv.art()

            # Upload the image
            upload_data = art.upload(
                image_data,
                file_type=file_type,
                matte=self.matte if self.matte != "none" else None,
            )
            logger.info("Upload response: %s", upload_data)

            # Try to extract content_id from upload response
            content_id = None
            if isinstance(upload_data, dict):
                content_id = upload_data.get("content_id")
            elif isinstance(upload_data, str):
                content_id = upload_data

            # Fallback: list uploaded art and pick the newest
            if not content_id:
                art_list = art.available("MY-C0002")
                if art_list:
                    latest = max(
                        art_list, key=lambda x: x.get("content_id", "")
                    )
                    content_id = latest["content_id"]

            if content_id:
                art.select_image(content_id, show=True)
                logger.info("Set active art to: %s", content_id)
                return content_id

            logger.warning("Could not determine content_id after upload")
            return "uploaded"
        finally:
            tv.close()

    def is_reachable(self) -> bool:
        """Check if the TV is reachable and paired on the network."""
        try:
            tv = self._connect()
            tv.rest_device_info()
            tv.close()
            return True
        except Exception:
            return False


def pair_tv(host: str, port: int = 8002, token_file: str = "token.txt") -> dict:
    """Initiate pairing with a Samsung TV.

    The TV will display a popup — the user must accept it on screen.
    Returns device info on success.
    """
    from samsungtvws import SamsungTVWS

    Path(token_file).parent.mkdir(parents=True, exist_ok=True)
    tv = SamsungTVWS(host=host, port=port, token_file=token_file)
    info = tv.rest_device_info()
    tv.close()
    return info
