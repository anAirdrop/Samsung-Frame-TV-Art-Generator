"""Validation tests for the Alexa interaction model."""

import json
from pathlib import Path

import pytest
from fastapi import HTTPException

from frame_art.config import Settings
from frame_art.routers import alexa


def _settings_without_alexa() -> Settings:
    return Settings()


def _load_intents() -> list[dict[str, object]]:
    model_path = Path(__file__).parents[1] / "alexa" / "skill.json"
    model = json.loads(model_path.read_text(encoding="utf-8"))
    return model["interactionModel"]["languageModel"]["intents"]


def test_search_query_samples_do_not_contain_another_slot() -> None:
    intents = _load_intents()

    for intent in intents:
        slots = intent.get("slots", [])
        search_query_slots = {
            slot["name"]
            for slot in slots
            if slot["type"] == "AMAZON.SearchQuery"
        }
        other_slots = {
            slot["name"]
            for slot in slots
            if slot["type"] != "AMAZON.SearchQuery"
        }

        for sample in intent.get("samples", []):
            contains_search_query = any(
                f"{{{slot_name}}}" in sample
                for slot_name in search_query_slots
            )
            contains_other_slot = any(
                f"{{{slot_name}}}" in sample for slot_name in other_slots
            )
            assert not (contains_search_query and contains_other_slot), sample


def test_art_description_and_room_use_separate_intents() -> None:
    intents = {intent["name"]: intent for intent in _load_intents()}

    generate_slots = intents["GenerateArtIntent"]["slots"]
    room_slots = intents["SelectRoomIntent"]["slots"]

    assert generate_slots == [
        {"name": "imageDescription", "type": "AMAZON.SearchQuery"}
    ]
    assert room_slots == [{"name": "roomName", "type": "ROOM_LIST"}]


def test_alexa_handler_requires_configured_skill_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(alexa, "_skill_handler", None)
    monkeypatch.setattr(alexa, "load_settings", _settings_without_alexa)

    with pytest.raises(HTTPException) as error:
        alexa._get_skill_handler()

    assert error.value.status_code == 503
