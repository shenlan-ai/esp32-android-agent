from __future__ import annotations

import math
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

Coordinate = StrictInt
StrokeCoordinate = Annotated[StrictInt, Field(ge=0, le=1000)]
MAX_PATH_POINTS = 20
MAX_PATH_REPORTS = 500
ACTION_FIELDS = {
    "tap": {"x", "y"},
    "long_press": {"x", "y", "duration_ms"},
    "swipe": {"x1", "y1", "x2", "y2", "duration_ms"},
    "path": {"points", "duration_ms"},
    "circle": {"x", "y", "r", "duration_ms"},
    "scroll": {"x", "y", "lines"},
    "type": {"text"},
    "key": {"key"},
    "home": set(),
    "back": set(),
    "recents": set(),
    "wait": {"duration_ms"},
}
KEYS = {
    "enter": 66,
    "backspace": 67,
    "esc": 111,
    "tab": 61,
    "space": 62,
    "up": 19,
    "down": 20,
    "left": 21,
    "right": 22,
    "volume_up": 24,
    "volume_down": 25,
}


class Action(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal[
        "tap", "swipe", "path", "circle", "long_press", "scroll", "type", "key", "home", "back", "recents", "wait"
    ]
    x: Coordinate | None = Field(None, ge=0, le=1000)
    y: Coordinate | None = Field(None, ge=0, le=1000)
    x1: Coordinate | None = Field(None, ge=0, le=1000)
    y1: Coordinate | None = Field(None, ge=0, le=1000)
    x2: Coordinate | None = Field(None, ge=0, le=1000)
    y2: Coordinate | None = Field(None, ge=0, le=1000)
    points: list[tuple[StrokeCoordinate, StrokeCoordinate]] | None = Field(
        None, min_length=2, max_length=MAX_PATH_POINTS
    )
    r: StrictInt | None = Field(None, ge=1, le=500)
    lines: StrictInt | None = Field(None, ge=-10, le=10)
    duration_ms: StrictInt = Field(350, ge=50, le=5000)
    text: str | None = Field(None, max_length=512)
    key: str | None = None
    frame_id: StrictInt | None = Field(None, ge=1)
    reason: str = Field("", max_length=500)
    expected: str = Field("", max_length=500)

    @model_validator(mode="after")
    def valid_arguments(self) -> Action:
        allowed = ACTION_FIELDS[self.action]
        required = allowed - {"duration_ms"}
        for key in required:
            if getattr(self, key) is None:
                raise ValueError(f"{self.action} requires {key}")
        provided = self.model_fields_set - {"action", "frame_id", "reason", "expected"}
        # Null fields from generated model schemas are harmless; other unrelated args are not.
        for key in provided - allowed:
            if getattr(self, key) is not None:
                raise ValueError(f"{self.action} does not accept {key}")
        if self.action == "type" and (
            not self.text or any(not 32 <= ord(c) <= 126 for c in self.text)
        ):
            raise ValueError("ASCII text only; Unicode requires an optional input method")
        if self.action == "key" and self.key not in KEYS:
            raise ValueError("Unsupported key")
        if self.action == "scroll" and self.lines == 0:
            raise ValueError("scroll lines cannot be zero")
        if self.action == "long_press" and self.duration_ms < 400:
            raise ValueError("long_press duration must be at least 400 ms")
        return self

    def stroke_points(self, width: int, height: int) -> list[tuple[int, int]]:
        if self.action == "path":
            return list(self.points)
        if self.action != "circle":
            raise ValueError("Action is not a continuous stroke")
        radius_y = self.r * width / height
        if (self.x - self.r < 0 or self.x + self.r > 1000
                or self.y - radius_y < 0 or self.y + radius_y > 1000):
            raise ValueError("Circle extends outside the screen")
        points = [
            (round(self.x + self.r * math.cos(i * math.tau / 16)),
             round(self.y + radius_y * math.sin(i * math.tau / 16)))
            for i in range(16)
        ]
        return [*points, points[0]]

    def arguments(self) -> dict:
        return {key: getattr(self, key) for key in ACTION_FIELDS[self.action]}


class DeviceInfo(BaseModel):
    serial: str
    state: str
    model: str = ""
    transport: Literal["usb", "wireless"]
