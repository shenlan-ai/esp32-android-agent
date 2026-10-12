import asyncio
import io

import pytest
from PIL import Image

from android_agent.models import DeviceInfo


def image_bytes(size=(200, 400), color="white"):
    stream = io.BytesIO()
    Image.new("RGB", size, color).save(stream, "PNG")
    return stream.getvalue()


class FakeAdb:
    available = True

    def __init__(self):
        self.calls = []
        self.png = image_bytes()
        self.screenshots = 0
        self.entries = [DeviceInfo(serial="phone1", state="device", transport="usb")]
        self.block_swipe = False
        self.swipe_started = asyncio.Event()

    async def devices(self):
        return self.entries

    async def run(self, *args, serial=None, timeout=None):
        self.calls.append((serial, args))
        if args == ("exec-out", "screencap", "-p"):
            self.screenshots += 1
            return self.png
        return b""

    async def shell(self, serial, *args):
        self.calls.append((serial, args))
        if "swipe" in args and self.block_swipe:
            self.swipe_started.set()
            await asyncio.Event().wait()
        return b""

    async def pair(self, address, code):
        return None

    async def connect(self, address):
        return None

    async def discover(self):
        return []

    async def stop(self):
        return None

    async def close(self):
        return None


@pytest.fixture
def fake_adb():
    return FakeAdb()
