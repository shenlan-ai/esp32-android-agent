from __future__ import annotations

import asyncio
import io
import time
from collections import deque
from dataclasses import dataclass

from PIL import Image, ImageChops, UnidentifiedImageError

from .errors import ScreenError, StaleFrameError


@dataclass(frozen=True)
class Frame:
    id: int
    serial: str
    received: float
    width: int
    height: int
    png: bytes
    jpeg: bytes
    dark: bool = False

    def public(self) -> dict:
        return {
            "id": self.id,
            "width": self.width,
            "height": self.height,
            "age_ms": round((time.monotonic() - self.received) * 1000),
            "dark": self.dark,
        }

    def pixel(self, x: int, y: int) -> tuple[int, int]:
        return round(x / 1000 * (self.width - 1)), round(y / 1000 * (self.height - 1))


def decode_frame(data: bytes, serial: str, sequence: int) -> Frame:
    try:
        with Image.open(io.BytesIO(data)) as original:
            if original.format != "PNG":
                raise ScreenError("ADB screenshot is not a PNG image")
            original.verify()
        with Image.open(io.BytesIO(data)) as original:
            original.load()
            if min(original.size) < 16 or max(original.size) > 8192:
                raise ScreenError("Screenshot dimensions are invalid")
            image = original.convert("RGB")
            gray = image.convert("L").resize((32, 32))
            dark = gray.getextrema()[1] < 8
            model_image = image.copy()
            model_image.thumbnail((1280, 1280))
            stream = io.BytesIO()
            model_image.save(stream, "JPEG", quality=85)
            return Frame(
                sequence,
                serial,
                time.monotonic(),
                image.width,
                image.height,
                data,
                stream.getvalue(),
                dark,
            )
    except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise ScreenError("Invalid or incomplete screenshot; reconnect the phone") from exc


def difference(a: Frame, b: Frame) -> float:
    if (a.width, a.height, a.serial) != (b.width, b.height, b.serial):
        return 255.0
    images = []
    for frame in (a, b):
        with Image.open(io.BytesIO(frame.png)) as image:
            images.append(image.convert("L").resize((64, 128)))
    pixels = ImageChops.difference(*images).tobytes()
    return sum(pixels) / len(pixels)


class AdbScreen:
    def __init__(self, adb, interval: float = 0.8):
        self.adb = adb
        self.interval = interval
        self.serial: str | None = None
        self.frame: Frame | None = None
        self._history: deque[Frame] = deque(maxlen=12)
        self._sequence = 0
        self._generation = 0
        self._lock = asyncio.Lock()

    def select(self, serial: str | None) -> None:
        self.serial = serial
        self.frame = None
        self._history.clear()
        self._generation += 1

    async def capture(self, force: bool = False) -> Frame:
        async with self._lock:
            if not self.serial:
                raise ScreenError("Select an authorized device first")
            if not force and self.frame and time.monotonic() - self.frame.received < self.interval:
                return self.frame
            generation, serial = self._generation, self.serial
            try:
                data = await self.adb.run("exec-out", "screencap", "-p", serial=serial)
                self._sequence += 1
                frame = await asyncio.to_thread(decode_frame, data, serial, self._sequence)
                if generation != self._generation:
                    raise StaleFrameError("Device changed while capturing; refresh the screen")
                self.frame = frame
                self._history.append(frame)
                return frame
            except BaseException:
                if generation == self._generation:
                    self.frame = None
                raise

    def validate_reference(self, frame_id: int | None, current: Frame) -> None:
        if frame_id is None:
            return
        previous = next((f for f in self._history if f.id == frame_id), None)
        if (
            previous is None
            or previous.serial != current.serial
            or (previous.width, previous.height) != (current.width, current.height)
            or time.monotonic() - previous.received > 15
        ):
            raise StaleFrameError(
                "The referenced screen is stale or rotated; refresh before operating"
            )
