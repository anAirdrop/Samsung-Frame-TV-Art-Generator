"""Alexa skill endpoint with ASK SDK request verification."""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ..config import Settings, load_config, resolve_room
from ..services.image_generator import generate_image
from ..services.image_processor import process_image
from ..services.notifier import Notifier, notify_failure, notify_success
from ..services.tv_controller import TVController

router = APIRouter()
logger = logging.getLogger(__name__)

# Lazy-initialized skill handler (built on first request)
_skill_handler = None


def _get_skill_handler():
    """Build the Alexa skill handler (lazy singleton)."""
    global _skill_handler
    if _skill_handler is not None:
        return _skill_handler

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
                "make an image of a sunset for the living room TV."
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
            description = slots["imageDescription"].value
            room = slots["roomName"].value

            if not description:
                return (
                    handler_input.response_builder.speak(
                        "I didn't catch the image description. Please try again."
                    )
                    .response
                )

            # Fire and forget — Alexa has an 8-second timeout, but image
            # generation can take 10-15 seconds. We acknowledge immediately
            # and send a push notification when done.
            asyncio.get_event_loop().create_task(
                _async_generate(description, room)
            )

            speech = (
                f"Got it! I'm generating {description} for your {room} TV. "
                "You'll get a notification when it's ready."
            )
            return handler_input.response_builder.speak(speech).response

    class HelpHandler(AbstractRequestHandler):
        def can_handle(self, handler_input):
            return is_intent_name("AMAZON.HelpIntent")(handler_input)

        def handle(self, handler_input):
            speech = (
                "You can say something like: make an image of a mountain "
                "landscape for the bedroom TV. What would you like to create?"
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
                "a sunset for the living room TV."
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
    sb.add_request_handler(LaunchHandler())
    sb.add_request_handler(GenerateArtIntentHandler())
    sb.add_request_handler(HelpHandler())
    sb.add_request_handler(CancelStopHandler())
    sb.add_request_handler(FallbackHandler())
    sb.add_exception_handler(CatchAllExceptionHandler())

    _skill_handler = WebserviceSkillHandler(skill=sb.create())
    return _skill_handler


async def _async_generate(description: str, room: str) -> None:
    """Background task: generate image, upload to TV, and notify."""
    settings = Settings()
    config = load_config()
    notifier = Notifier(settings.ntfy_server, settings.ntfy_topic)

    tv_key = resolve_room(room, config.tvs)
    if not tv_key:
        await notify_failure(notifier, f"Unknown room: {room}")
        return

    tv_config = config.tvs[tv_key]
    tv_display_name = tv_key.replace("_", " ").title()

    try:
        raw_image = await generate_image(
            description=description,
            config=config,
            settings=settings,
            model_override=None,
        )
        processed = process_image(raw_image, config.image.output)

        controller = TVController(tv_config)
        await asyncio.to_thread(
            controller.upload_and_display,
            processed,
            file_type=config.image.output.format,
        )
        await notify_success(notifier, description, tv_display_name)

    except Exception as e:
        logger.exception("Async Alexa generation failed")
        await notify_failure(notifier, str(e))


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
