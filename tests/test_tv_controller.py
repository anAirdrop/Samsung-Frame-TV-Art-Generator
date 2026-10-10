"""Tests for Samsung TV controller service."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from frame_art.config import TVConfig
from frame_art.services.tv_controller import TVController, pair_tv


@patch("frame_art.services.tv_controller.TVController._connect")
def test_upload_and_display_with_content_id(mock_connect):
    mock_tv = MagicMock()
    mock_art = MagicMock()
    mock_art.upload.return_value = "MY_ART_001"
    mock_tv.art.return_value = mock_art
    mock_connect.return_value = mock_tv

    config = TVConfig(host="192.168.1.100", token_file="/tmp/token.txt")
    controller = TVController(config)
    result = controller.upload_and_display(b"fake-image", file_type="JPEG")

    mock_art.upload.assert_called_once()
    mock_art.select_image.assert_called_once_with("MY_ART_001", show=True)
    assert result == "MY_ART_001"
    mock_tv.close.assert_called_once()


@patch("frame_art.services.tv_controller.TVController._connect")
def test_upload_without_content_id_raises(mock_connect):
    mock_tv = MagicMock()
    mock_art = MagicMock()
    mock_art.upload.return_value = None
    mock_tv.art.return_value = mock_art
    mock_connect.return_value = mock_tv

    config = TVConfig(host="192.168.1.100", token_file="/tmp/token.txt")
    controller = TVController(config)

    with pytest.raises(RuntimeError, match="did not return a content ID"):
        controller.upload_and_display(b"fake-image", "JPEG")

    mock_art.select_image.assert_not_called()
    mock_tv.close.assert_called_once()


@patch("frame_art.services.tv_controller.TVController._connect")
def test_is_reachable_success(mock_connect):
    mock_tv = MagicMock()
    mock_tv.rest_device_info.return_value = {"device": {"name": "Frame TV"}}
    mock_connect.return_value = mock_tv

    config = TVConfig(host="192.168.1.100", token_file="/tmp/token.txt")
    controller = TVController(config)
    assert controller.is_reachable() is True


@patch("frame_art.services.tv_controller.TVController._connect")
def test_is_reachable_failure(mock_connect):
    mock_tv = MagicMock()
    mock_tv.rest_device_info.side_effect = ConnectionRefusedError()
    mock_connect.return_value = mock_tv

    config = TVConfig(host="192.168.1.100", token_file="/tmp/token.txt")
    controller = TVController(config)
    assert controller.is_reachable() is False


@patch("samsungtvws.SamsungTVWS")
def test_pair_tv_opens_websocket_to_receive_token(
    samsung_tv_class: MagicMock, tmp_path: Path
) -> None:
    tv = samsung_tv_class.return_value
    tv.rest_device_info.return_value = {"device": {"name": "Frame TV"}}
    token_file = str(tmp_path / "tokens" / "frame.txt")

    result = pair_tv("192.168.1.100", 8002, token_file)

    samsung_tv_class.assert_called_once_with(
        host="192.168.1.100",
        port=8002,
        token_file=token_file,
        timeout=30,
    )
    tv.open.assert_called_once_with()
    assert result == {"device": {"name": "Frame TV"}}
    tv.close.assert_called_once_with()
