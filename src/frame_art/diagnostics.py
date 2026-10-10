"""Sanitized Samsung Frame compatibility diagnostics."""

from __future__ import annotations

import json
import logging

from .config import load_config, load_settings
from .services.tv_controller import TVController

logger = logging.getLogger(__name__)


def collect_diagnostics() -> dict[str, object]:
    """Collect model and Art API information without secrets or private IPs."""
    settings = load_settings()
    config = load_config(settings.config_path)
    televisions: dict[str, object] = {}
    for tv_key, tv_config in config.tvs.items():
        try:
            televisions[tv_key] = TVController(tv_config).diagnostics()
        except Exception as error:
            logger.exception(
                "TV diagnostics failed", extra={"tv_key": tv_key}
            )
            televisions[tv_key] = {
                "status": "error",
                "error_type": type(error).__name__,
                "message": str(error),
            }
    return {"televisions": televisions}


def main() -> None:
    """Print diagnostics suitable for reviewing before an issue report."""
    print(json.dumps(collect_diagnostics(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
