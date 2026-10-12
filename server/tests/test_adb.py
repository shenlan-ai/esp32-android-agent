import asyncio
import shlex

import pytest

from android_agent.adb import AdbClient, validate_address
from android_agent.errors import DeviceError


@pytest.mark.parametrize(
    "value", ["x;id:123", "127.0.0.1:0", "127.0.0.1:65536", "999.2.3.4:123", "-x:20", "x:1&&id"]
)
def test_address_rejects_invalid_input(value):
    with pytest.raises(ValueError):
        validate_address(value)


def test_address_accepts_host_and_ip():
    assert validate_address("192.168.1.2:37123") == "192.168.1.2:37123"
    assert validate_address("phone.local:5555") == "phone.local:5555"


async def test_shell_quotes_remote_arguments(monkeypatch):
    adb = AdbClient()
    calls = []

    async def run(*args, **kwargs):
        calls.append(args)
        return b""

    monkeypatch.setattr(adb, "run", run)
    text = "hello'; touch /sdcard/unwanted; '"
    await adb.shell("phone", "input", "text", text)
    assert calls[0] == ("shell", "input", "text", shlex.quote(text))
    assert shlex.split(" ".join(calls[0][1:])) == ["input", "text", text]


async def test_device_states_are_not_assumed_online(monkeypatch):
    adb = AdbClient()

    async def run(*args, **kwargs):
        return b"List of devices attached\nabc unauthorized usb:1\n192.168.1.2:456 device model:Pixel_6\nxyz offline\n"

    monkeypatch.setattr(adb, "run", run)
    entries = await adb.devices()
    assert [entry.state for entry in entries] == ["unauthorized", "device", "offline"]
    assert entries[1].transport == "wireless"


async def test_pairing_validates_code_before_running(monkeypatch):
    adb = AdbClient()
    with pytest.raises(ValueError):
        await adb.pair("phone:1234", "bad;code")


async def test_timed_out_process_is_killed(monkeypatch):
    class Process:
        returncode = None

        def kill(self):
            self.returncode = -1

        async def communicate(self):
            if self.returncode is None:
                await asyncio.sleep(10)
            return b"", b""

    process = Process()

    async def spawn(*args, **kwargs):
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    monkeypatch.setattr(AdbClient, "available", property(lambda _: True))
    adb = AdbClient(timeout=0.01)
    with pytest.raises(DeviceError, match="may have run"):
        await adb.run("shell", "input", "tap", "1", "1")
    assert process.returncode == -1
    assert not adb._processes
