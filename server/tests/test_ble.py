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
from android_agent.usb import UsbBridge

SESSION = "a" * 32


class FakeSerial:
    def __init__(self, **kwargs):
        self.lines = queue.Queue()
        self.writes = []
        self.closed = False
        self.auto_complete = True
        self.active = None
        self.chip = "esp32"
        self.firmware = "0.1.0"
        self.include_firmware = True
        self.release_sent = True
        self.include_ble_state = False
        self.ble_state = None
        self.capabilities = ["tap", "type", "key", "swipe", "wait"]

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
                        **({"ble_state": self.ble_state} if self.include_ble_state else {}),
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
                capabilities=self.capabilities,
                **({"firmware": self.firmware} if self.include_firmware else {}),
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
    obj.firmware = "0.1.0"
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


async def test_path_negotiates_and_serializes_once_then_cancels():
    serial = FakeSerial()
    serial.firmware = "0.1.4"
    serial.capabilities.append("path")
    obj = SerialBridge("COM5", factory=lambda **kwargs: serial)
    try:
        await obj.open()
        control = BleController(obj, "phone1", calibration().model_copy(update={"firmware": "0.1.4"}))
        assert {"path", "circle"} <= set(control.capabilities)
        serial.auto_complete = False
        action = asyncio.create_task(control.execute(Action(action="path", points=[[0, 0], [100, 300], [500, 300]]), frame()))
        for _ in range(100):
            if serial.active:
                break
            await asyncio.sleep(.01)
        assert serial.active["points"] == [[0, 0], [80, 360], [400, 360]]
        action.cancel()
        with pytest.raises(asyncio.CancelledError):
            await action
        assert not serial.active
        assert len([p for p in serial.writes if p["op"] == "action"]) == 1
        assert (await obj.stop())["release"] == "hid_release_sent"
    finally:
        await obj.close()


BLE_STATE = {"link": True, "authenticated": True, "keyboard_subscribed": True,
             "mouse_subscribed": True, "auth_error": None}


async def test_diagnostics_handshake_and_heartbeat_update_without_secrets():
    serial = FakeSerial()
    serial.include_ble_state = True
    serial.ble_state = {**BLE_STATE, "mac": "private", "key": "private"}
    obj = SerialBridge("COM5", factory=lambda **kwargs: serial)
    try:
        await obj.open()
        assert obj.public()["ble_state"] == BLE_STATE
        snapshot = obj.public()["ble_state"]
        snapshot["link"] = False
        assert obj.public()["ble_state"]["link"] is True
        if obj._heartbeat:
            obj._heartbeat.cancel()
            await asyncio.gather(obj._heartbeat, return_exceptions=True)
        serial.ble_state = {**BLE_STATE, "authenticated": False, "auth_error": 5}
        serial.emit({"id": 0}, "heartbeat", ble_connected=False)
        for _ in range(100):
            if obj.public()["ble_state"] == serial.ble_state:
                break
            await asyncio.sleep(0.01)
        assert obj.public()["ble_state"] == serial.ble_state
        controller = BleController(obj, "phone1", calibration())
        assert controller.capabilities == []
        obj._fail("lost")
        assert obj.ble_state is None and obj.public()["ble_state"] is None
    finally:
        await obj.close()


@pytest.mark.parametrize("value", [
    None, [], True, {}, {**BLE_STATE, "link": 1}, {**BLE_STATE, "authenticated": "true"},
    {**BLE_STATE, "keyboard_subscribed": None}, {**BLE_STATE, "mouse_subscribed": 0},
    {**BLE_STATE, "auth_error": True}, {**BLE_STATE, "auth_error": -1},
    {**BLE_STATE, "auth_error": 256}, {**BLE_STATE, "auth_error": "5"},
    {key: val for key, val in BLE_STATE.items() if key != "auth_error"},
])
async def test_invalid_diagnostics_clear_previous_snapshot_without_breaking_legacy_hid(bridge, value):
    bridge.ble_state = BLE_STATE.copy()
    bridge.device.emit({"id": 0}, "heartbeat", ble_state=value)
    for _ in range(100):
        if bridge.ble_state is None:
            break
        await asyncio.sleep(0.01)
    assert bridge.public()["ble_state"] is None
    assert bridge.connected and bridge.hid_ready
    await BleController(bridge, "phone1").execute(Action(action="type", text="test"), frame())
    assert len([p for p in bridge.device.writes if p["op"] == "action"]) == 1


async def test_missing_diagnostics_clear_and_diagnostic_ready_cannot_authorize_input(bridge):
    bridge.ble_state = BLE_STATE.copy()
    bridge._receive(json.dumps({"v": 1, "session": SESSION, "id": 0,
                               "status": "heartbeat", "ble_connected": True}).encode())
    assert bridge.public()["ble_state"] is None
    bridge._receive(json.dumps({"v": 1, "session": SESSION, "id": 0,
                               "status": "heartbeat", "ble_connected": False,
                               "ble_state": BLE_STATE}).encode())
    assert bridge.public()["ble_state"] == BLE_STATE and not bridge.hid_ready
    controller = BleController(bridge, "phone1", calibration())
    assert controller.capabilities == []
    with pytest.raises(DeviceError, match="unavailable"):
        await controller.execute(Action(action="tap", x=500, y=500), frame())
    assert not [p for p in bridge.device.writes if p["op"] == "action"]


def test_usb_does_not_store_ble_diagnostics():
    obj = UsbBridge(AsyncMock(), AsyncMock(), "001122aabbcc")
    obj.session = SESSION
    obj._receive(json.dumps({"v": 1, "session": SESSION, "id": 0,
                            "status": "heartbeat", "usb_connected": True,
                            "ble_state": BLE_STATE}).encode())
    assert obj.connected and obj.hid_ready and obj.ble_state is None
    assert "ble_state" not in obj.public()


async def test_accepted_is_not_done_and_timeout_never_replays(bridge):
    bridge.device.auto_complete = False
    with pytest.raises(DeviceError, match="unknown"):
        await bridge.request("action", action="type", text="hello", timeout=0.04)
    assert len([p for p in bridge.device.writes if p["op"] == "action"]) == 1
    assert not bridge.connected
    with pytest.raises(DeviceError):
        await bridge.request("action", action="type", text="hello")
    assert len(bridge.device.writes) == 1


@pytest.mark.parametrize("included,version", [
    (False, "0.1.0"), (True, None), (True, {"version": "0.1.0"}),
    (True, "unknown"), (True, "UNKNOWN"), (True, ""),
    (True, "bad version"), (True, "x" * 65),
])
async def test_unknown_handshake_keeps_keyboard_but_rejects_saved_coordinates(included, version):
    serial = FakeSerial()
    serial.include_firmware, serial.firmware = included, version
    obj = SerialBridge("COM5", factory=lambda **kwargs: serial)
    try:
        await obj.open()
        assert obj.connected and obj.firmware == ""
        controller = BleController(obj, "phone1", calibration())
        assert "tap" not in controller.capabilities
        with pytest.raises(DeviceError):
            await controller.execute(Action(action="tap", x=500, y=500), frame())
        assert not [p for p in serial.writes if p["op"] == "action"]
        await controller.execute(Action(action="type", text="test"), frame())
        assert len([p for p in serial.writes if p["op"] == "action"]) == 1
    finally:
        await obj.close()
    assert serial.closed


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


async def test_new_pacing_firmware_rejects_legacy_calibration_before_input(bridge):
    bridge.firmware = "0.1.1"
    controller = BleController(bridge, "phone1", calibration())
    assert "tap" not in controller.capabilities and "type" in controller.capabilities
    with pytest.raises(DeviceError):
        await controller.execute(Action(action="tap", x=500, y=500), frame())
    assert not bridge.device.writes
    controller.calibration = calibration().model_copy(update={"firmware": "0.1.1"})
    assert "tap" in controller.capabilities
    await controller.execute(Action(action="tap", x=500, y=500), frame())
    assert len([p for p in bridge.device.writes if p["op"] == "action"]) == 1


async def test_calibration_uses_handshake_version_and_rejects_spoofing(bridge, fake_adb):
    session = DeviceSession(fake_adb, AdbScreen(fake_adb))
    await session.select("phone1")
    bridge.firmware = "0.1.1"
    session.controller = BleController(bridge, "phone1")
    saved = await session.calibrate(calibration())
    assert saved.firmware == "0.1.1" and session.controller.calibration is saved
    with pytest.raises(DeviceError, match="firmware"):
        await session.calibrate(calibration().model_copy(update={"firmware": "0.1.0"}))
    assert session.controller.calibration is saved


async def test_public_calibration_and_persisted_settings_match_firmware(bridge, fake_adb, tmp_path):
    import httpx

    from android_agent.app import create_app
    from android_agent.config import ConfigStore, RuntimeSettings

    app = create_app(RuntimeSettings(data_dir=tmp_path), fake_adb)
    async with app.router.lifespan_context(app), httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://localhost"
    ) as client:
        await app.state.session.select("phone1")
        bridge.firmware = "0.1.1"
        app.state.session.controller = BleController(bridge, "phone1", calibration())
        await app.state.session.screen.capture(force=True)
        before = (await client.get("/api/status")).json()
        assert not before["calibrated"] and "tap" not in before["capabilities"]
        client.headers["X-Agent-CSRF"] = (await client.get("/api/session")).json()["csrf"]
        response = await client.post("/api/control/calibrate", json=calibration().model_dump())
        assert response.status_code == 200
        after = (await client.get("/api/status")).json()
        assert after["calibrated"] and "tap" in after["capabilities"]
        assert ConfigStore(tmp_path).load().ble_calibrations["phone1"].firmware == "0.1.1"


@pytest.mark.parametrize("mode", ["ble", "usb"])
@pytest.mark.parametrize("version", ["", "unknown", "UNKNOWN", "bad version", "x" * 65])
async def test_unknown_firmware_api_preserves_saved_calibration(mode, version, bridge, fake_adb, tmp_path):
    import httpx

    from android_agent.app import create_app
    from android_agent.config import ConfigStore, Preferences, RuntimeSettings
    from android_agent.usb import UsbController

    saved = calibration().model_copy(update={"firmware": "0.1.1"})
    board_id = "001122aabbcc"
    store = ConfigStore(tmp_path)
    prefs = Preferences(ble_calibrations={"phone1": saved},
                        usb_calibrations={f"{board_id}:phone1": saved})
    store.save(prefs)
    previous = store.path.read_bytes()
    app = create_app(RuntimeSettings(data_dir=tmp_path), fake_adb)
    async with app.router.lifespan_context(app), httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://localhost"
    ) as client:
        await app.state.session.select("phone1")
        bridge.firmware, bridge.board_id = version, board_id
        controller = (BleController if mode == "ble" else UsbController)(bridge, "phone1", saved)
        app.state.session.controller = controller
        await app.state.session.screen.capture(force=True)
        client.headers["X-Agent-CSRF"] = (await client.get("/api/session")).json()["csrf"]
        response = await client.post("/api/control/calibrate", json=calibration().model_dump())
        assert response.status_code == 409
        assert "firmware" in response.json()["detail"].lower()
        assert controller.calibration is saved
        assert app.state.preferences.ble_calibrations == prefs.ble_calibrations
        assert app.state.preferences.usb_calibrations == prefs.usb_calibrations
        assert store.path.read_bytes() == previous
        status = (await client.get("/api/status")).json()
        assert not status["calibrated"] and "tap" not in status["capabilities"]
        with pytest.raises(DeviceError):
            await app.state.session.execute(Action(action="tap", x=500, y=500))
        assert not [p for p in bridge.device.writes if p["op"] == "action"]
        await app.state.session.execute(Action(action="type", text="test"))
        assert len([p for p in bridge.device.writes if p["op"] == "action"]) == 1


@pytest.mark.parametrize("version", ["0.1.1-dev+board_1", "a" * 64])
async def test_valid_development_handshake_can_bind_coordinates(version):
    serial = FakeSerial()
    serial.firmware = version
    obj = SerialBridge("COM5", factory=lambda **kwargs: serial)
    try:
        await obj.open()
        assert obj.firmware == version
        saved = calibration().model_copy(update={"firmware": version})
        controller = BleController(obj, "phone1", saved)
        await controller.execute(Action(action="tap", x=500, y=500), frame())
        assert len([p for p in serial.writes if p["op"] == "action"]) == 1
        assert not saved.model_copy(update={"firmware": "unknown"}).compatible_firmware("unknown")
    finally:
        await obj.close()


@pytest.mark.parametrize("mode,coordinate_timeout", [("ble", 60), ("usb", 30)])
async def test_transport_deadline_for_pointer_and_keyboard(mode, coordinate_timeout):
    from types import SimpleNamespace

    from android_agent.usb import UsbController

    bridge = SimpleNamespace(connected=True, hid_ready=True, firmware="0.1.1",
                             capabilities=["tap", "type"], request=AsyncMock(return_value={}))
    controller_class = BleController if mode == "ble" else UsbController
    controller = controller_class(bridge, "phone1", calibration().model_copy(update={"firmware": "0.1.1"}))
    await controller.execute(Action(action="tap", x=500, y=500), frame())
    assert bridge.request.await_args.kwargs["timeout"] == coordinate_timeout
    await controller.execute(Action(action="type", text="test"), frame())
    assert bridge.request.await_args.kwargs["timeout"] == 30
    await controller.locate(PointerProbe(x=100, y=100))
    assert bridge.request.await_args.kwargs["timeout"] == coordinate_timeout


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
