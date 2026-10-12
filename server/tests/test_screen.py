import asyncio

import pytest
from conftest import image_bytes

from android_agent.errors import ScreenError, StaleFrameError
from android_agent.screen import AdbScreen, decode_frame


def test_corrupt_screenshot_is_rejected():
    with pytest.raises(ScreenError):
        decode_frame(image_bytes()[:40], "phone", 1)


def test_pixel_mapping_includes_last_pixel():
    frame = decode_frame(image_bytes(), "phone", 1)
    assert frame.pixel(0, 0) == (0, 0)
    assert frame.pixel(1000, 1000) == (199, 399)


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
