"""Alexa skill endpoint with ASK SDK request verification."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

from ..config import load_config, load_settings, resolve_room
from ..storage import JobStore

router = APIRouter()
logger = logging.getLogger(__name__)
_PENDING_DESCRIPTION_KEY = "pending_image_description"

# Lazy-initialized skill handler (built on first request)
_skill_handler = None


def _get_skill_handler():
    """Build the Alexa skill handler (lazy singleton)."""
    global _skill_handler
    if _skill_handler is not None:
        return _skill_handler

    skill_id = load_settings().alexa_skill_id.strip()
    if not skill_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Alexa is not configured. Set ALEXA_SKILL_ID and restart "
                "Frame Art."
            ),
        )

    from ask_sdk_core.dispatch_components import (
        AbstractExceptionHandler,
        AbstractRequestHandler,
    )
    from ask_sdk_core.skill_builder import SkillBuilder
    from ask_sdk_core.utils import is_intent_name, is_request_type
    from ask_sdk_webservice_support.webservice_handler import (
        WebserviceSkillHandler,
    )

    class LaunchHandler(AbstractRequestHandler):
        def can_handle(self, handler_input):
            return is_request_type("LaunchRequest")(handler_input)

        def handle(self, handler_input):
            speech = (
                "Welcome to Frame Art. Say something like: "
                "make an image of a sunset. I'll then ask which room."
            )
            return (
                handler_input.response_builder.speak(speech)
                .ask(speech)
                .response
            )

    class GenerateArtIntentHandler(AbstractRequestHandler):
        def can_handle(self, handler_input):
            return is_intent_name("GenerateArtIntent")(handler_input)

        def handle(self, handler_input):
            slots = handler_input.request_envelope.request.intent.slots
            description_slot = slots.get("imageDescription")
            description = (
                description_slot.value.strip()
                if description_slot and description_slot.value
                else None
            )

            if not description:
                speech = (
                    "I didn't catch the image description. What would you "
                    "like me to create?"
                )
                return (
                    handler_input.response_builder.speak(speech)
                    .ask(speech)
                    .response
                )

            handler_input.attributes_manager.session_attributes[
                _PENDING_DESCRIPTION_KEY
            ] = description
            speech = f"Which room should I display {description} in?"
            return (
                handler_input.response_builder.speak(speech)
                .ask(speech)
                .response
            )

    class SelectRoomIntentHandler(AbstractRequestHandler):
        def can_handle(self, handler_input):
            return is_intent_name("SelectRoomIntent")(handler_input)

        def handle(self, handler_input):
            slots = handler_input.request_envelope.request.intent.slots
            room_slot = slots.get("roomName")
            room = (
                room_slot.value.strip()
                if room_slot and room_slot.value
                else None
            )
            description = handler_input.attributes_manager.session_attributes.get(
                _PENDING_DESCRIPTION_KEY
            )

            if not description:
                speech = (
                    "First tell me what image to create. For example, say: "
                    "make an image of a sunset."
                )
                return (
                    handler_input.response_builder.speak(speech)
                    .ask(speech)
                    .response
                )

            if not room:
                speech = "I didn't catch the room. Which TV should I use?"
                return (
                    handler_input.response_builder.speak(speech)
                    .ask(speech)
                    .response
                )

            settings = load_settings()
            config = load_config(settings.config_path)
            tv_key = resolve_room(room, config.tvs)
            if tv_key is None:
                known_rooms = ", ".join(
                    key.replace("_", " ") for key in config.tvs
                )
                speech = (
                    f"I don't have a TV configured for {room}. "
                    f"Try one of these rooms: {known_rooms}."
                )
                return (
                    handler_input.response_builder.speak(speech)
                    .ask("Which room should I use?")
                    .response
                )

            store = JobStore(settings.database_path)
            store.initialize()
            store.enqueue(description, tv_key, "alexa")

            speech = (
                f"Got it! I'm creating {description} for your {room} TV. "
                "You can check the TV in a moment."
            )
            return handler_input.response_builder.speak(speech).response

    class HelpHandler(AbstractRequestHandler):
        def can_handle(self, handler_input):
            return is_intent_name("AMAZON.HelpIntent")(handler_input)

        def handle(self, handler_input):
            speech = (
                "You can say: make an image of a mountain landscape. "
                "I'll then ask which room. What would you like to create?"
            )
            return (
                handler_input.response_builder.speak(speech)
                .ask(speech)
                .response
            )

    class CancelStopHandler(AbstractRequestHandler):
        def can_handle(self, handler_input):
            return is_intent_name("AMAZON.CancelIntent")(
                handler_input
            ) or is_intent_name("AMAZON.StopIntent")(handler_input)

        def handle(self, handler_input):
            return (
                handler_input.response_builder.speak("Goodbye!").response
            )

    class FallbackHandler(AbstractRequestHandler):
        def can_handle(self, handler_input):
            return is_intent_name("AMAZON.FallbackIntent")(handler_input)

        def handle(self, handler_input):
            speech = (
                "I'm not sure what you mean. Try saying: make an image of "
                "a sunset. I'll then ask which room."
            )
            return (
                handler_input.response_builder.speak(speech)
                .ask(speech)
                .response
            )

    class CatchAllExceptionHandler(AbstractExceptionHandler):
        def can_handle(self, handler_input, exception):
            return True

        def handle(self, handler_input, exception):
            logger.exception("Alexa skill error")
            return (
                handler_input.response_builder.speak(
                    "Sorry, something went wrong. Please try again."
                )
                .response
            )

    sb = SkillBuilder()
    sb.skill_id = skill_id
    sb.add_request_handler(LaunchHandler())
    sb.add_request_handler(GenerateArtIntentHandler())
    sb.add_request_handler(SelectRoomIntentHandler())
    sb.add_request_handler(HelpHandler())
    sb.add_request_handler(CancelStopHandler())
    sb.add_request_handler(FallbackHandler())
    sb.add_exception_handler(CatchAllExceptionHandler())

    _skill_handler = WebserviceSkillHandler(skill=sb.create())
    return _skill_handler


@router.post("/api/alexa")
async def alexa_webhook(request: Request) -> JSONResponse:
    """Handle incoming Alexa skill requests with signature verification."""
    handler = _get_skill_handler()
    body = await request.body()
    headers = dict(request.headers)

    response = handler.verify_request_and_dispatch(
        headers, body.decode("utf-8")
    )
    return JSONResponse(content=json.loads(response))
