"""First-run local setup and Samsung TV pairing routes."""

from __future__ import annotations

import asyncio
import ipaddress
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import HTMLResponse

from ..config import (
    AppConfig,
    TVConfig,
    generate_webhook_secret,
    load_settings,
    room_key,
    save_config,
    save_secrets,
)
from ..models import DiscoveredTV, SetupRequest, SetupResponse
from ..services.discovery import discover_samsung_tvs
from ..services.tv_controller import pair_tv

router = APIRouter()
_SETUP_PAGE = Path(__file__).parents[1] / "templates" / "setup.html"


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def setup_page() -> HTMLResponse:
    """Serve the local first-run setup page."""
    return HTMLResponse(_SETUP_PAGE.read_text(encoding="utf-8"))


@router.get("/api/setup/status", include_in_schema=False)
async def setup_status() -> dict[str, bool]:
    """Report whether initial setup has been completed."""
    settings = load_settings()
    return {
        "configured": settings.config_path.exists()
        and settings.secrets_path.exists()
    }


@router.get(
    "/api/setup/discover",
    response_model=list[DiscoveredTV],
    include_in_schema=False,
)
async def discover_tvs(request: Request) -> list[DiscoveredTV]:
    """Find Samsung televisions visible on the local network."""
    _ensure_setup_available(request)
    return await asyncio.to_thread(discover_samsung_tvs, 3.0)


@router.post(
    "/api/setup/configure",
    response_model=SetupResponse,
    include_in_schema=False,
)
async def configure_installation(
    payload: SetupRequest, request: Request
) -> SetupResponse:
    """Pair one TV and persist a secure initial installation."""
    _ensure_setup_available(request)
    settings = load_settings()
    key = room_key(payload.room_name)
    token_path = settings.data_dir / "tokens" / f"{key}_token.txt"
    token_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        await asyncio.to_thread(
            pair_tv,
            str(payload.tv_host),
            payload.tv_port,
            str(token_path),
        )
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "TV pairing failed. Confirm the TV is on, uses the same network, "
                "and that you accepted its pairing prompt."
            ),
        ) from error

    aliases = _unique_aliases(payload.room_name, payload.aliases)
    config = AppConfig(
        tvs={
            key: TVConfig(
                host=str(payload.tv_host),
                port=payload.tv_port,
                token_file=str(token_path),
                aliases=aliases,
                matte="none",
            )
        }
    )
    webhook_secret = generate_webhook_secret()
    save_config(config, settings.config_path)
    save_secrets(settings, payload.fal_key.strip(), webhook_secret)
    return SetupResponse(
        status="configured",
        room=payload.room_name.strip(),
        api_key=webhook_secret,
        test_prompt=payload.test_prompt.strip(),
    )


def _ensure_setup_available(request: Request) -> None:
    settings = load_settings()
    if settings.config_path.exists() or settings.secrets_path.exists():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Setup is already complete",
        )
    if request.headers.get("cf-connecting-ip") or request.headers.get(
        "x-forwarded-for"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Initial setup is not available through a public proxy",
        )
    client_host = request.client.host if request.client is not None else ""
    if not _is_private_client(client_host):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Initial setup is only available from the local network",
        )


def _is_private_client(host: str) -> bool:
    if host in {"localhost", "testclient"}:
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return address.is_private or address.is_loopback or address.is_link_local


def _unique_aliases(room_name: str, aliases: list[str]) -> list[str]:
    candidates = [room_name, *aliases]
    result: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        normalized = candidate.strip().lower()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result
