"""Tests for Samsung TV controller service."""

from unittest.mock import MagicMock, patch

from frame_art.config import TVConfig
from frame_art.services.tv_controller import TVController


@patch("frame_art.services.tv_controller.TVController._connect")
def test_upload_and_display_with_content_id(mock_connect):
    mock_tv = MagicMock()
    mock_art = MagicMock()
    mock_art.upload.return_value = {"content_id": "MY_ART_001"}
    mock_tv.art.return_value = mock_art
    mock_connect.return_value = mock_tv

    config = TVConfig(host="192.168.1.100")
    controller = TVController(config)
    result = controller.upload_and_display(b"fake-image", file_type="JPEG")

    mock_art.upload.assert_called_once()
    mock_art.select_image.assert_called_once_with("MY_ART_001", show=True)
    assert result == "MY_ART_001"
    mock_tv.close.assert_called_once()


@patch("frame_art.services.tv_controller.TVController._connect")
def test_upload_fallback_to_art_list(mock_connect):
    mock_tv = MagicMock()
    mock_art = MagicMock()
    # upload returns None — no content_id in response
    mock_art.upload.return_value = None
    mock_art.available.return_value = [
        {"content_id": "ART_001"},
        {"content_id": "ART_002"},
    ]
    mock_tv.art.return_value = mock_art
    mock_connect.return_value = mock_tv

    config = TVConfig(host="192.168.1.100")
    controller = TVController(config)
    result = controller.upload_and_display(b"fake-image")

    mock_art.available.assert_called_once_with("MY-C0002")
    mock_art.select_image.assert_called_once_with("ART_002", show=True)
    assert result == "ART_002"


@patch("frame_art.services.tv_controller.TVController._connect")
def test_is_reachable_success(mock_connect):
    mock_tv = MagicMock()
    mock_tv.rest_device_info.return_value = {"device": {"name": "Frame TV"}}
    mock_connect.return_value = mock_tv

    config = TVConfig(host="192.168.1.100")
    controller = TVController(config)
    assert controller.is_reachable() is True


@patch("frame_art.services.tv_controller.TVController._connect")
def test_is_reachable_failure(mock_connect):
    mock_tv = MagicMock()
    mock_tv.rest_device_info.side_effect = ConnectionRefusedError()
    mock_connect.return_value = mock_tv

    config = TVConfig(host="192.168.1.100")
    controller = TVController(config)
    assert controller.is_reachable() is False
