from __future__ import annotations

import asyncio
import re

from .errors import DeviceError
from .models import ACTION_FIELDS, KEYS, Action
from .screen import Frame


class AdbController:
    mode = "adb"

    def __init__(self, adb, serial: str):
        self.adb, self.serial = adb, serial
        self._last_touch: tuple[int, int] | None = None

    @property
    def capabilities(self) -> list[str]:
        return [name for name in ACTION_FIELDS if name not in {"path", "circle"}]

    async def execute(self, action: Action, frame: Frame) -> None:
        name = action.action
        if name == "wait":
            await asyncio.sleep(action.duration_ms / 1000)
            return
        if name in {"tap", "long_press"}:
            x, y = frame.pixel(action.x, action.y)
            self._last_touch = x, y
            args = (
                ("tap", str(x), str(y))
                if name == "tap"
                else ("swipe", str(x), str(y), str(x), str(y), str(action.duration_ms))
            )
            await self.adb.shell(self.serial, "input", "touchscreen", *args)
        elif name == "swipe":
            x1, y1 = frame.pixel(action.x1, action.y1)
            x2, y2 = frame.pixel(action.x2, action.y2)
            self._last_touch = x2, y2
            await self.adb.shell(
                self.serial,
                "input",
                "touchscreen",
                "swipe",
                str(x1),
                str(y1),
                str(x2),
                str(y2),
                str(action.duration_ms),
            )
        elif name == "scroll":
            y1 = max(200, min(800, action.y))
            y2 = max(50, min(950, y1 + action.lines * 80))
            await self.execute(
                Action(action="swipe", x1=action.x, y1=y1, x2=action.x, y2=y2, duration_ms=350),
                frame,
            )
        elif name == "type":
            # Android input text treats %s as a space. Split literal %s to preserve it.
            for part in re.split(r"(%s)", action.text):
                chunks = ["%", "s"] if part == "%s" else [part]
                for chunk in chunks:
                    if chunk:
                        await self.adb.shell(self.serial, "input", "text", chunk.replace(" ", "%s"))
        else:
            keys = {"home": 3, "back": 4, "recents": 187}
            key = KEYS[action.key] if name == "key" else keys[name]
            await self.adb.shell(self.serial, "input", "keyevent", str(key))
        self._last_touch = None

    async def stop(self) -> dict:
        await self.adb.stop()
        release = "no_held_input"
        if self._last_touch:
            try:
                x, y = self._last_touch
                await self.adb.shell(
                    self.serial, "input", "touchscreen", "motionevent", "UP", str(x), str(y)
                )
                release = "up_event_sent"
            except DeviceError:
                release = "unconfirmed_device_release"
            self._last_touch = None
        return {"cancelled": True, "release": release}
