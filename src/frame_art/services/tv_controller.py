"""Samsung Frame TV controller — upload art and set it as active display."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ..config import TVConfig

logger = logging.getLogger(__name__)


class TVController:
    """Manages communication with a single Samsung Frame TV."""

    def __init__(self, tv_config: TVConfig) -> None:
        self.host = tv_config.host
        self.port = tv_config.port
        self.token_file = tv_config.token_file
        self.matte = tv_config.matte

    def _ensure_token_dir(self) -> None:
        if self.token_file:
            Path(self.token_file).parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> Any:
        from samsungtvws import SamsungTVWS

        self._ensure_token_dir()
        return SamsungTVWS(
            host=self.host,
            port=self.port,
            token_file=self.token_file or None,
            timeout=20,
        )

    def upload_and_display(
        self, image_data: bytes, file_type: str
    ) -> str:
        """Upload an image to the TV and set it as the active art.

        Returns the content_id of the uploaded image.
        """
        tv = self._connect()
        try:
            art = tv.art()

            # Upload the image
            content_id = art.upload(
                image_data,
                file_type=file_type,
                matte=self.matte if self.matte != "none" else None,
            )
            if not content_id:
                raise RuntimeError(
                    f"TV at {self.host}:{self.port} accepted the upload but did not "
                    "return a content ID"
                )

            art.select_image(content_id, show=True)
            logger.info(
                "Artwork selected",
                extra={"content_id": content_id, "host": self.host},
            )
            return content_id
        finally:
            tv.close()

    def delete_artwork(self, content_id: str) -> None:
        """Delete one artwork previously uploaded by this application."""
        tv = self._connect()
        try:
            deleted = tv.art().delete(content_id)
            if not deleted:
                raise RuntimeError(
                    f"TV at {self.host}:{self.port} did not confirm deletion of "
                    f"artwork '{content_id}'"
                )
        finally:
            tv.close()

    def is_reachable(self) -> bool:
        """Check if the TV is reachable and paired on the network."""
        tv = None
        try:
            tv = self._connect()
            tv.rest_device_info()
            return True
        except Exception as error:
            logger.warning(
                "TV reachability check failed",
                extra={"host": self.host, "port": self.port, "error": str(error)},
            )
            return False
        finally:
            if tv is not None:
                tv.close()

    def diagnostics(self) -> dict[str, object]:
        """Return sanitized device and Art API compatibility information."""
        tv = self._connect()
        try:
            response = tv.rest_device_info()
            device = response.get("device", {})
            art = tv.art()
            return {
                "name": device.get("name", "Unknown"),
                "model": device.get("modelName", "Unknown"),
                "firmware": device.get("firmwareVersion", "Unknown"),
                "frame_tv_support": device.get("FrameTVSupport", "Unknown"),
                "art_api_version": art.get_api_version(),
                "art_api_supported": art.supported(),
            }
        finally:
            tv.close()


def pair_tv(host: str, port: int, token_file: str) -> dict[str, Any]:
    """Initiate pairing with a Samsung TV.

    The TV will display a popup — the user must accept it on screen.
    Returns device info on success.
    """
    from samsungtvws import SamsungTVWS

    Path(token_file).parent.mkdir(parents=True, exist_ok=True)
    tv = SamsungTVWS(
        host=host,
        port=port,
        token_file=token_file,
        timeout=30,
    )
    try:
        tv.open()
        return tv.rest_device_info()
    finally:
        tv.close()
