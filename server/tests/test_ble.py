from __future__ import annotations

import asyncio
import json
import queue
import time
from unittest.mock import AsyncMock

import pytest

from android_agent.ble import BleController, Calibration, PointerProbe, SerialBridge
from android_agent.errors import DeviceError
from android_agent.models import Action
from android_agent.screen import AdbScreen, Frame
from android_agent.session import DeviceSession

SESSION = "a" * 32


class FakeSerial:
    def __init__(self, **kwargs):
        self.lines = queue.Queue()
        self.writes = []
        self.closed = False
        self.auto_complete = True
        self.active = None
        self.chip = "esp32"
        self.release_sent = True

    def open(self):
        pass

    def reset_input_buffer(self):
        pass

    def close(self):
        self.closed = True

    def read(self, count):
        if self.closed:
            raise OSError("disconnected")
        try:
            return self.lines.get(timeout=0.02)
        except queue.Empty:
            return b""

    def emit(self, payload, status, **extra):
        self.lines.put(
            (
                json.dumps(
                    {
                        "v": 1,
                        "session": SESSION,
                        "id": payload["id"],
                        "status": status,
                        "ble_connected": True,
                        **extra,
                    }
                )
                + "\n"
            ).encode()
        )

    def write(self, data):
        payload = json.loads(data)
        self.writes.append(payload)
        op = payload["op"]
        if op == "hello":
            self.emit(
                payload,
                "hello",
                chip=self.chip,
                firmware="test",
                capabilities=["tap", "type", "key", "swipe", "wait"],
            )
        elif op == "heartbeat":
            self.emit(payload, "heartbeat")
        elif op == "stop":
            if self.active:
                self.emit(self.active, "cancelled")
                self.active = None
            self.emit(payload, "stopped", release_sent=self.release_sent)
        elif op == "action":
            self.active = payload
            self.emit(payload, "accepted")
            if self.auto_complete:
                self.emit(payload, "done")
                self.active = None
        return len(data)


@pytest.fixture
async def bridge():
    obj = SerialBridge("COM5")
    obj.device = FakeSerial()
    obj.session = SESSION
    obj.ble_connected = True
    obj.capabilities = ["tap", "type", "key", "wait", "swipe"]
    obj._reader = asyncio.create_task(obj._read())
    yield obj
    await obj.close()


def frame(width=200, height=400, phone="phone1"):
    return Frame(1, phone, time.monotonic(), width, height, b"", b"")


def calibration():
    return Calibration(phone="phone1", width=200, height=400, counts_x=800, counts_y=1200)


async def test_handshake_checks_chip_and_negotiates_capabilities():
    serial = FakeSerial()
    obj = SerialBridge("COM5", factory=lambda **kwargs: serial)
    try:
        await obj.open()
        assert obj.connected and obj.ble_connected
        assert "tap" in obj.capabilities
        assert obj.device.dtr is False and obj.device.rts is False
    finally:
        await obj.close()
    assert serial.closed


async def test_accepted_is_not_done_and_timeout_never_replays(bridge):
    bridge.device.auto_complete = False
    with pytest.raises(DeviceError, match="unknown"):
        await bridge.request("action", action="type", text="hello", timeout=0.04)
    assert len([p for p in bridge.device.writes if p["op"] == "action"]) == 1
    assert not bridge.connected
    with pytest.raises(DeviceError):
        await bridge.request("action", action="type", text="hello")
    assert len(bridge.device.writes) == 1


async def test_stop_interrupts_action_and_confirms_release(bridge):
    bridge.device.auto_complete = False
    action = asyncio.create_task(bridge.request("action", action="type", text="hello"))
    for _ in range(50):
        if bridge.device.active:
            break
        await asyncio.sleep(0.005)
    result = await bridge.stop()
    assert result["release"] == "hid_release_sent"
    with pytest.raises(DeviceError, match="cancelled"):
        await action
    assert not bridge.device.active


async def test_stop_does_not_claim_a_failed_release_was_sent(bridge):
    bridge.device.release_sent = False
    assert (await bridge.stop())["release"] == "unconfirmed_hid_release"


async def test_hid_report_failure_is_not_action_success(bridge):
    bridge.device.auto_complete = False
    action = asyncio.create_task(bridge.request("action", action="type", text="hello"))
    await asyncio.sleep(0.03)
    bridge.device.emit(bridge.device.active, "error", error="hid_report_failed")
    with pytest.raises(DeviceError, match="not submitted"):
        await action
    assert not bridge.connected
    assert len(bridge.device.writes) == 1


async def test_cancelled_request_does_not_replay_or_break_stop(bridge):
    bridge.device.auto_complete = False
    action = asyncio.create_task(bridge.request("action", action="tap", x=1, y=1))
    await asyncio.sleep(0.03)
    action.cancel()
    with pytest.raises(asyncio.CancelledError):
        await action
    assert not bridge._pending
    assert not bridge.device.active
    assert (await bridge.stop())["release"] == "hid_release_sent"
    assert len([p for p in bridge.device.writes if p["op"] == "action"]) == 1


async def test_stale_session_invalidates_link(bridge):
    bridge.device.lines.put(
        (
            json.dumps(
                {"v": 1, "session": "b" * 32, "id": 0, "status": "heartbeat", "ble_connected": True}
            )
            + "\n"
        ).encode()
    )
    await asyncio.sleep(0.03)
    assert not bridge.connected
    assert "session changed" in bridge.public()["error"]
    assert (await bridge.stop())["release"] == "unconfirmed_board_watchdog_release"


async def test_missing_heartbeat_ack_invalidates_link(bridge):
    bridge._last_heartbeat = time.monotonic() - 3
    await bridge._pulse()
    assert not bridge.connected
    assert not bridge.device.writes


async def test_rotation_and_phone_binding_reject_before_write(bridge):
    controller = BleController(bridge, "phone1", calibration())
    for current in (frame(400, 200), frame(phone="phone2")):
        with pytest.raises(DeviceError):
            await controller.execute(Action(action="tap", x=500, y=500), current)
    assert not bridge.device.writes


async def test_calibration_and_capabilities_are_explicit(bridge):
    controller = BleController(bridge, "phone1")
    assert "tap" not in controller.capabilities
    with pytest.raises(DeviceError):
        await controller.execute(Action(action="tap", x=500, y=500), frame())
    controller.calibration = calibration()
    await controller.execute(Action(action="tap", x=500, y=500), frame())
    written = [p for p in bridge.device.writes if p["op"] == "action"][0]
    assert (written["x"], written["y"]) == (400, 600)
    for action in (Action(action="home"), Action(action="key", key="volume_up")):
        with pytest.raises(DeviceError):
            await controller.execute(action, frame())


async def test_phone_selection_closes_ble_and_requires_explicit_rebind(fake_adb):
    session = DeviceSession(fake_adb, AdbScreen(fake_adb))
    await session.select("phone1")
    bridge = SerialBridge("COM5")
    bridge.close = AsyncMock()
    session.controller = BleController(bridge, "phone1", calibration())
    await session.select("phone1")
    bridge.close.assert_awaited_once()
    assert session.controller.mode == "adb"


async def test_probe_never_clicks(bridge):
    controller = BleController(bridge, "phone1")
    await controller.locate(PointerProbe(x=800, y=0))
    assert bridge.device.writes[0]["action"] == "locate"


async def test_serial_loss_fails_pending_without_replay(bridge):
    bridge.device.auto_complete = False
    action = asyncio.create_task(bridge.request("action", action="wait", duration_ms=5000))
    await asyncio.sleep(0.03)
    bridge.device.closed = True
    with pytest.raises(DeviceError, match="connection lost"):
        await action
    assert len(bridge.device.writes) == 1


async def test_oversized_response_fails_closed(bridge):
    bridge.device.lines.put(b"x" * 1025)
    await asyncio.sleep(0.03)
    assert not bridge.connected


async def test_invalid_ble_state_not_treated_as_connected(bridge):
    bridge.device.lines.put(
        (
            json.dumps(
                {
                    "v": 1,
                    "session": SESSION,
                    "id": 0,
                    "status": "heartbeat",
                    "ble_connected": "false",
                }
            )
            + "\n"
        ).encode()
    )
    await asyncio.sleep(0.03)
    assert not bridge.connected
