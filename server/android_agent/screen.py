from __future__ import annotations

import asyncio
import io
import time
from collections import deque
from dataclasses import dataclass

from PIL import Image, ImageChops, ImageDraw, UnidentifiedImageError

from .errors import ScreenError, StaleFrameError
from .models import Action


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


def coordinate_image(frame: Frame) -> bytes:
    """Annotate only the actor's copy, in the full screenshot's 0..1000 space."""
    with Image.open(io.BytesIO(frame.jpeg)) as source:
        image = source.convert("RGB")
    width, height = image.size
    draw = ImageDraw.Draw(image, "RGBA")
    for value in range(0, 1001, 100):
        x, y = round(value * (width - 1) / 1000), round(value * (height - 1) / 1000)
        draw.line((x, 0, x, height - 1), fill=(0, 105, 200, 90))
        draw.line((0, y, width - 1, y), fill=(0, 105, 200, 90))
        label = str(value)
        box = draw.textbbox((0, 0), label)
        tw, th = box[2] - box[0] + 4, box[3] - box[1] + 4
        for lx, ly in [(min(x, width - tw), 0), (0, min(y, height - th))]:
            draw.rectangle((lx, ly, lx + tw, ly + th), fill=(0, 65, 130, 240))
            draw.text((lx + 2, ly + 2 - box[1]), label, fill=(255, 255, 255, 255))
    output = io.BytesIO()
    image.save(output, "JPEG", quality=90)
    return output.getvalue()


def validate_decision(reference: Frame, current: Frame, action: Action) -> None:
    if ((reference.serial, reference.width, reference.height)
            != (current.serial, current.width, current.height)
            or time.monotonic() - reference.received > 60):
        raise StaleFrameError("Decision screen is stale or rotated; observe again")
    if current.dark:
        raise ScreenError("Screen is dark or protected; unlock the phone before continuing")
    crop = None
    if action.action in {"tap", "long_press"}:
        x, y = current.pixel(action.x, action.y)
        rx, ry = max(24, current.width // 20), max(24, current.height // 20)
        crop = (max(0, x-rx), max(0, y-ry), min(current.width, x+rx), min(current.height, y+ry))
    images = []
    for frame in (reference, current):
        with Image.open(io.BytesIO(frame.png)) as image:
            region = image.crop(crop) if crop else image
            images.append(region.convert("RGB").resize((96, 96) if crop else (128, 256)))
    pixels = ImageChops.difference(*images).tobytes()
    mean = sum(pixels) / len(pixels)
    fraction = sum(p > 18 for p in pixels) / len(pixels)
    if mean > 4 or fraction > 0.04:
        raise StaleFrameError("Relevant screen content changed while the model was thinking")


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
