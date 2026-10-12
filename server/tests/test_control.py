import asyncio

import pytest
from pydantic import ValidationError

from android_agent.errors import DeviceError
from android_agent.models import Action, DeviceInfo
from android_agent.screen import AdbScreen
from android_agent.session import DeviceSession


@pytest.mark.parametrize(
    "payload",
    [
        {"action": "tap", "x": 1001, "y": 1},
        {"action": "tap", "x": True, "y": 1},
        {"action": "tap", "x": 1},
        {"action": "type", "text": "中文"},
        {"action": "type", "text": "x\nkey enter"},
        {"action": "key", "key": "cmd+h"},
        {"action": "long_press", "x": 1, "y": 2},
        {"action": "home", "text": "extra"},
    ],
)
def test_invalid_actions_are_rejected(payload):
    with pytest.raises(ValidationError):
        Action.model_validate(payload)


async def test_literal_percent_s_is_preserved(fake_adb):
    session = DeviceSession(fake_adb, AdbScreen(fake_adb))
    await session.select("phone1")
    await session.execute(Action(action="type", text="a %s b"))
    text_args = [args[-1] for _, args in fake_adb.calls if args[:2] == ("input", "text")]
    assert text_args == ["a%s", "%", "s", "%sb"]


async def test_unauthorized_device_cannot_be_selected(fake_adb):
    fake_adb.entries = [DeviceInfo(serial="phone1", state="unauthorized", transport="usb")]
    session = DeviceSession(fake_adb, AdbScreen(fake_adb))
    with pytest.raises(DeviceError, match="unauthorized"):
        await session.select("phone1")
    assert session.serial is None


async def test_stop_invalidates_queued_actions(fake_adb):
    session = DeviceSession(fake_adb, AdbScreen(fake_adb))
    await session.select("phone1")
    fake_adb.block_swipe = True
    first = asyncio.create_task(session.execute(Action(action="swipe", x1=10, y1=20, x2=30, y2=40)))
    await fake_adb.swipe_started.wait()
    second = asyncio.create_task(session.execute(Action(action="tap", x=500, y=500)))
    await asyncio.sleep(0)
    result = await session.stop()
    outcomes = await asyncio.gather(first, second, return_exceptions=True)
    assert isinstance(outcomes[0], asyncio.CancelledError)
    assert isinstance(outcomes[1], DeviceError)
    assert result["release"] == "up_event_sent"
    assert not any(args[:3] == ("input", "touchscreen", "tap") for _, args in fake_adb.calls)


async def test_new_action_is_rejected_until_release_finishes(fake_adb):
    session = DeviceSession(fake_adb, AdbScreen(fake_adb))
    await session.select("phone1")
    started, finish = asyncio.Event(), asyncio.Event()

    async def delayed_release():
        started.set()
        await finish.wait()
        return {"release": "confirmed"}

    session.controller.stop = delayed_release
    stopping = asyncio.create_task(session.stop())
    await started.wait()
    with pytest.raises(DeviceError, match="releasing"):
        await session.execute(Action(action="home"))
    finish.set()
    await stopping
