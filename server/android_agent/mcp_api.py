"""Private HTTP bridge for MCP; hardware and observations stay in the web process."""
from __future__ import annotations

import base64
import secrets
import time
from collections import OrderedDict
from dataclasses import dataclass

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field

from .ble import KEYS as HID_KEYS
from .errors import DeviceError, ScreenError, StaleFrameError
from .models import ACTION_EXAMPLES, KEYS, Action
from .screen import Frame

MAX_OBSERVATIONS = 8
OBSERVATION_TTL = 60


class ObservedAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    observation_id: str = Field(min_length=20, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")
    action: Action


@dataclass(frozen=True)
class Observation:
    frame: Frame
    binding: tuple[int, int]


class ObservationStore:
    def __init__(self):
        self.frames: OrderedDict[str, Observation] = OrderedDict()

    def add(self, frame: Frame, binding: tuple[int, int]) -> str:
        self.frames = OrderedDict(
            (key, value) for key, value in self.frames.items()
            if time.monotonic() - value.frame.received <= OBSERVATION_TTL
            and value.binding == binding
        )
        key = secrets.token_urlsafe(32)
        self.frames[key] = Observation(frame, binding)
        while len(self.frames) > MAX_OBSERVATIONS:
            self.frames.popitem(last=False)
        return key

    def get(self, key: str) -> Observation:
        value = self.frames.get(key)
        if value is None or time.monotonic() - value.frame.received > OBSERVATION_TTL:
            raise StaleFrameError("Observation expired or already used; take a new screenshot")
        return value

    def consume(self, key: str) -> None:
        if self.frames.pop(key, None) is None:
            raise StaleFrameError("Observation already used; take a new screenshot")


def register_mcp_routes(app: FastAPI) -> None:
    @app.get("/api/mcp/status")
    async def status():
        session = app.state.session
        controller = session.controller
        board = getattr(controller, "bridge", None)
        connected = False
        if session.serial:
            try:
                connected = any(d.serial == session.serial and d.state == "device"
                                for d in await session.adb.devices())
            except DeviceError:
                pass
        capabilities = list(controller.capabilities) if connected and controller and not app.state.firmware.busy else []
        allowed_keys = HID_KEYS if controller and controller.mode in {"ble", "usb"} else set(KEYS)
        return {
            "selected": bool(session.serial),
            "connected": connected,
            "mode": controller.mode if controller else None,
            "capabilities": capabilities,
            "allowed_keys": sorted(allowed_keys) if "key" in capabilities else [],
            "action_examples": {name: ACTION_EXAMPLES[name] for name in capabilities},
            "action_rules": {
                **({"path": "One continuous pressed stroke through 2..20 integer [x,y] pairs; release only at the end. Long paths may exceed the calibrated movement budget."} if "path" in capabilities else {}),
                **({"circle": "r is a radius in normalized x units (1..500), preserving a round shape in screen pixels. Keep the whole shape inside the image and within the calibrated movement budget."} if "circle" in capabilities else {}),
            },
            "task_state": app.state.runner.state,
            "maintenance": app.state.firmware.busy,
            "hid_ready": bool(board.hid_ready) if board else None,
            "frame": session.screen.frame.public() if session.screen.frame else None,
            "coordinates": "Integers 0..1000 over the entire screenshot, including system bars",
            "text": "Printable ASCII; switch the phone IME to English manually",
        }

    @app.post("/api/mcp/screenshot")
    async def screenshot():
        try:
            frame, binding = await app.state.session.observe()
            if frame.dark:
                raise ScreenError("Screen is dark or protected; unlock the phone and observe again")
        except ScreenError:
            app.state.mcp_observations.frames.clear()
            await app.state.runner.stop()
            raise
        key = app.state.mcp_observations.add(frame, binding)
        return {
            "observation_id": key,
            "frame": frame.public(),
            "expires_in_seconds": OBSERVATION_TTL,
            "coordinates": "0..1000 over the entire image; scale pixels using width-1 and height-1",
            "mime_type": "image/jpeg",
            "image_base64": base64.b64encode(frame.jpeg).decode("ascii"),
        }

    @app.post("/api/mcp/action")
    async def action(payload: ObservedAction):
        if payload.action.frame_id is not None:
            raise ValueError("Use observation_id, not action.frame_id")
        observation = app.state.mcp_observations.get(payload.observation_id)
        try:
            result = await app.state.session.execute(
                payload.action, reference=observation.frame, binding=observation.binding,
                on_submit=lambda _: app.state.mcp_observations.consume(payload.observation_id),
            )
        except StaleFrameError:
            # A scene-change rejection does not cancel someone else's valid input.
            raise
        except ScreenError:
            app.state.mcp_observations.frames.clear()
            await app.state.runner.stop()
            raise
        return {**result, "verification": "Input completed; take a new screenshot to verify the phone result"}
