import asyncio
import io

import pytest
from conftest import image_bytes
from PIL import Image

from android_agent.errors import ScreenError, StaleFrameError
from android_agent.screen import AdbScreen, coordinate_image, decode_frame


def test_corrupt_screenshot_is_rejected():
    with pytest.raises(ScreenError):
        decode_frame(image_bytes()[:40], "phone", 1)


def test_pixel_mapping_includes_last_pixel():
    frame = decode_frame(image_bytes(), "phone", 1)
    assert frame.pixel(0, 0) == (0, 0)
    assert frame.pixel(1000, 1000) == (199, 399)


@pytest.mark.parametrize("size", [(1080, 2400), (2400, 1080), (200, 400)])
def test_coordinate_guides_preserve_image_space_and_originals(size):
    frame = decode_frame(image_bytes(size), "phone", 1)
    png, jpeg = frame.png, frame.jpeg
    guided = coordinate_image(frame)
    with Image.open(io.BytesIO(jpeg)) as original, Image.open(io.BytesIO(guided)) as image:
        assert image.size == original.size
        assert image.getpixel((0, 0)) != original.getpixel((0, 0))
        # A midpoint guide aligns with the same normalized screenshot midpoint.
        width, height = image.size
        middle = (round((width - 1) / 2), round((height - 1) / 2))
        assert image.getpixel(middle) != original.getpixel(middle)
        # Content away from guides remains visible, without an added border.
        assert image.getpixel((round(width * .45), round(height * .45)))[0] > 220
    assert frame.png == png and frame.jpeg == jpeg


async def test_preview_concurrency_uses_cache(fake_adb):
    screen = AdbScreen(fake_adb)
    screen.select("phone1")
    frames = await asyncio.gather(*[screen.capture() for _ in range(5)])
    assert fake_adb.screenshots == 1
    assert len({frame.id for frame in frames}) == 1


async def test_rotation_invalidates_reference(fake_adb):
    screen = AdbScreen(fake_adb)
    screen.select("phone1")
    first = await screen.capture()
    fake_adb.png = image_bytes((400, 200))
    second = await screen.capture(force=True)
    with pytest.raises(StaleFrameError):
        screen.validate_reference(first.id, second)


async def test_failed_capture_clears_current_frame(fake_adb):
    screen = AdbScreen(fake_adb)
    screen.select("phone1")
    await screen.capture()
    fake_adb.png = b"not an image"
    with pytest.raises(ScreenError):
        await screen.capture(force=True)
    assert screen.frame is None
