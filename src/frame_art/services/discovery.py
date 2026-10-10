"""Local-network discovery for Samsung televisions."""

from __future__ import annotations

import json
import socket
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from ..models import DiscoveredTV

_SSDP_ADDRESS = ("239.255.255.250", 1900)
_SSDP_MESSAGE = (
    "M-SEARCH * HTTP/1.1\r\n"
    "HOST: 239.255.255.250:1900\r\n"
    'MAN: "ssdp:discover"\r\n'
    "MX: 2\r\n"
    "ST: ssdp:all\r\n\r\n"
).encode("ascii")


def discover_samsung_tvs(timeout_seconds: float) -> list[DiscoveredTV]:
    """Discover Frame-capable Samsung TVs using SSDP and their REST API."""
    locations = _discover_locations(timeout_seconds)
    discovered: list[DiscoveredTV] = []
    for location in sorted(locations):
        tv = _load_tv_details(location)
        if tv is not None:
            discovered.append(tv)
    return discovered


def _discover_locations(timeout_seconds: float) -> set[str]:
    deadline = time.monotonic() + timeout_seconds
    locations: set[str] = set()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as discovery_socket:
        discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        discovery_socket.settimeout(0.25)
        discovery_socket.sendto(_SSDP_MESSAGE, _SSDP_ADDRESS)
        while time.monotonic() < deadline:
            try:
                payload, _ = discovery_socket.recvfrom(65535)
            except TimeoutError:
                continue
            headers = _parse_ssdp_headers(payload.decode("utf-8", errors="ignore"))
            location = headers.get("location")
            if location:
                locations.add(location)
    return locations


def _parse_ssdp_headers(payload: str) -> dict[str, str]:
    headers: dict[str, str] = {}
    for line in payload.splitlines()[1:]:
        name, separator, value = line.partition(":")
        if separator:
            headers[name.strip().lower()] = value.strip()
    return headers


def _load_tv_details(location: str) -> DiscoveredTV | None:
    parsed = urlparse(location)
    if not parsed.hostname:
        return None
    api_url = f"http://{parsed.hostname}:8001/api/v2/"
    try:
        response = httpx.get(api_url, timeout=2.0)
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
    except (httpx.HTTPError, json.JSONDecodeError, ValueError):
        return None

    device = payload.get("device")
    if not isinstance(device, dict):
        return None
    if str(device.get("OS", "")).lower() != "tizen":
        return None
    frame_support = str(device.get("FrameTVSupport", "")).lower() == "true"
    if not frame_support:
        support = payload.get("isSupport", "{}")
        try:
            support_data = json.loads(support) if isinstance(support, str) else support
            frame_support = (
                str(support_data.get("FrameTVSupport", "")).lower() == "true"
            )
        except json.JSONDecodeError:
            frame_support = False
    return DiscoveredTV(
        host=parsed.hostname,
        name=str(device.get("name") or payload.get("name") or "Samsung TV"),
        model=str(device.get("modelName") or "Unknown"),
        frame_support=frame_support,
    )
