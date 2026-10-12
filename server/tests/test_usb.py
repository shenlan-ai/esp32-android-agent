from __future__ import annotations

import asyncio
import json
import secrets
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from android_agent.app import create_app
from android_agent.ble import Calibration
from android_agent.config import ConfigStore, Preferences, RuntimeSettings
from android_agent.errors import DeviceError
from android_agent.models import Action
from android_agent.screen import AdbScreen
from android_agent.session import DeviceSession
from android_agent.usb import UsbController, UsbListener, authentication_proof

KEY, BOARD = "a" * 64, "001122aabbcc"


async def until(predicate):
    for _ in range(100):
        if predicate():
            return
        await asyncio.sleep(0.01)
    raise AssertionError("Timed out waiting for test bridge")


class FakeUsbBoard:
    def __init__(self):
        self.session = secrets.token_hex(16)
        self.requests = []
        self.active = None
        self.auto_complete = True
        self.heartbeat_ack = True
        self.release_sent = True
        self.task = None
        self.writer = None

    async def connect(self, listener, key=KEY):
        self.reader, self.writer = await asyncio.open_connection("127.0.0.1", listener.port)
        self.challenge = json.loads(await self.reader.readline())
        self.writer.write((json.dumps({"v": 1, "op": "authenticate", "board_id": BOARD,
                           "proof": authentication_proof(key, self.challenge["nonce"], BOARD)}) + "\n").encode())
        await self.writer.drain()
        self.task = asyncio.create_task(self.run())

    async def emit(self, payload, status, **extra):
        self.writer.write((json.dumps({"v": 1, "session": self.session, "id": payload["id"],
                           "status": status, "usb_connected": True, **extra}) + "\n").encode())
        await self.writer.drain()

    async def run(self):
        try:
            while line := await self.reader.readline():
                obj = json.loads(line)
                self.requests.append(obj)
                if obj["op"] == "hello":
                    await self.emit(obj, "hello", chip="esp32s3", board_id=BOARD,
                                    profile="test", firmware="test", capabilities=["tap", "type", "wait", "key", "swipe"])
                elif obj["op"] == "heartbeat" and self.heartbeat_ack:
                    await self.emit(obj, "heartbeat")
                elif obj["op"] == "status":
                    await self.emit(obj, "ready")
                elif obj["op"] == "stop":
                    if self.active:
                        await self.emit(self.active, "cancelled")
                        self.active = None
                    await self.emit(obj, "stopped", release_sent=self.release_sent)
                elif obj["op"] == "action":
                    self.active = obj
                    await self.emit(obj, "accepted")
                    if self.auto_complete:
                        await self.emit(obj, "done", elapsed_ms=100, button_held_ms=60)
                        self.active = None
        except (OSError, asyncio.CancelledError):
            pass

    async def close(self):
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
        if self.task:
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)


@pytest.fixture
async def connection():
    listener, board = UsbListener("127.0.0.1", 0), FakeUsbBoard()
    await listener.start(KEY, BOARD)
    await board.connect(listener)
    await until(lambda: listener.current is not None)
    yield listener, board, listener.current
    await asyncio.wait_for(listener.close(), 3)
    await board.close()


async def test_authenticated_handshake_and_live_heartbeat(connection):
    listener, board, bridge = connection
    assert bridge.connected and bridge.hid_ready
    assert bridge.board_id == BOARD and "tap" in bridge.capabilities
    await until(lambda: any(obj["op"] == "heartbeat" for obj in board.requests))
    assert KEY not in json.dumps(listener.public())
    assert bridge.public()["usb_connected"] is True


@pytest.mark.parametrize("kind", ["wrong_key", "wrong_board", "replay", "large", "version_bool"])
async def test_authentication_rejects_before_control(kind):
    listener = UsbListener("127.0.0.1", 0)
    await listener.start(KEY, BOARD)
    writer = None
    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", listener.port)
        challenge = json.loads(await reader.readline())
        nonce = "f" * 64 if kind == "replay" else challenge["nonce"]
        proof = authentication_proof("b" * 64 if kind == "wrong_key" else KEY, nonce, BOARD)
        payload = {"v": True if kind == "version_bool" else 1, "op": "authenticate",
                   "board_id": "bad" if kind == "wrong_board" else BOARD, "proof": proof}
        writer.write(b"x" * 1025 + b"\n" if kind == "large" else (json.dumps(payload) + "\n").encode())
        await writer.drain()
        assert await asyncio.wait_for(reader.read(), 1) == b""
        assert listener.current is None
    finally:
        if writer:
            writer.close()
            await writer.wait_closed()
        await listener.close()


async def test_active_connection_cannot_be_replaced(connection):
    listener, _, bridge = connection
    reader, writer = await asyncio.open_connection("127.0.0.1", listener.port)
    challenge = json.loads(await reader.readline())
    writer.write((json.dumps({"v": 1, "op": "authenticate", "board_id": BOARD,
                             "proof": authentication_proof(KEY, challenge["nonce"], BOARD)}) + "\n").encode())
    await writer.drain()
    assert await asyncio.wait_for(reader.read(), 1) == b""
    assert listener.current is bridge and bridge.connected
    writer.close()
    await writer.wait_closed()


async def test_shutdown_closes_incomplete_handshakes():
    listener = UsbListener("127.0.0.1", 0)
    await listener.start(KEY, BOARD)
    reader, writer = await asyncio.open_connection("127.0.0.1", listener.port)
    await reader.readline()  # Leave authentication intentionally unfinished.
    await asyncio.wait_for(listener.close(), 2)
    assert await reader.read() == b""
    assert not listener._clients
    writer.close()
    await writer.wait_closed()


async def test_action_cancel_stops_without_replay(connection):
    _, board, bridge = connection
    board.auto_complete = False
    task = asyncio.create_task(bridge.request("action", action="swipe", x=100, y=100, x2=200, y2=200, duration_ms=5000))
    await until(lambda: board.active is not None)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert not board.active
    assert len([r for r in board.requests if r["op"] == "action"]) == 1
    assert (await bridge.stop())["release"] == "hid_release_sent"
    board.release_sent = False
    assert (await bridge.stop())["release"] == "unconfirmed_hid_release"


async def test_timeout_closes_stream_and_does_not_replay(connection):
    _, board, bridge = connection
    board.auto_complete = False
    with pytest.raises(DeviceError, match="unknown"):
        await bridge.request("action", timeout=0.05, action="type", text="hello")
    assert not bridge.connected and bridge.writer.is_closing()
    with pytest.raises(DeviceError):
        await bridge.request("action", action="type", text="hello")
    assert len([r for r in board.requests if r["op"] == "action"]) == 1


@pytest.mark.parametrize("extra", [{"session": "b" * 32}, {"usb_connected": "true"}, {"status": "error", "error": "hid_report_failed"}])
async def test_invalid_session_readiness_or_report_failure_invalidates(connection, extra):
    _, board, bridge = connection
    await board.emit({"id": 0}, extra.get("status", "heartbeat"), **{k: v for k, v in extra.items() if k != "status"})
    await until(lambda: not bridge.connected)
    assert bridge.writer.is_closing()


async def test_lost_heartbeat_closes_without_resending(connection):
    _, board, bridge = connection
    bridge._heartbeat.cancel()
    await asyncio.gather(bridge._heartbeat, return_exceptions=True)
    board.heartbeat_ack = False
    await asyncio.sleep(0.02)  # Drain the acknowledgement already sent by the fixture.
    bridge._last_heartbeat -= 3
    await bridge._pulse()
    assert not bridge.connected
    assert bridge.writer.is_closing()
    assert not any(obj["op"] == "action" for obj in board.requests)


async def test_usb_requires_wireless_and_rebind_after_disconnect(connection, fake_adb):
    listener, board, bridge = connection
    session = DeviceSession(fake_adb, AdbScreen(fake_adb))
    await session.select("phone1")
    with pytest.raises(DeviceError, match="wireless"):
        await session.set_mode("usb", bridge)
    assert session.controller.mode == "adb"
    fake_adb.entries[0].transport = "wireless"
    await session.set_mode("usb", bridge)
    assert "tap" not in session.controller.capabilities
    await session.calibrate(Calibration(phone="phone1", width=200, height=400, counts_x=800, counts_y=1200))
    assert "tap" in session.controller.capabilities
    await session.execute(Action(action="tap", x=500, y=500))
    sent = next(r for r in board.requests if r["op"] == "action")
    assert (sent["x"], sent["y"]) == (400, 600)
    await board.close()
    await until(lambda: not bridge.connected)
    replacement = FakeUsbBoard()
    try:
        await replacement.connect(listener)
        await until(lambda: listener.current is not bridge)
        assert session.controller.mode == "usb" and session.controller.bridge is bridge
        assert not session.controller.capabilities
        await session.set_mode("usb", listener.current)
        assert session.controller.bridge is listener.current
        assert "tap" not in session.controller.capabilities
    finally:
        await session.close()
        await replacement.close()


async def test_board_port_conflict_does_not_break_app(tmp_path, fake_adb):
    # Test the listener's bounded error separately; the API lifespan catches it.
    occupied = await asyncio.start_server(lambda r, w: w.close(), "127.0.0.1", 0)
    port = occupied.sockets[0].getsockname()[1]
    listener = UsbListener("127.0.0.1", port)
    try:
        with pytest.raises(DeviceError, match="port unavailable"):
            await listener.start(KEY, BOARD)
        assert listener.error and not listener.server
    finally:
        occupied.close()
        await occupied.wait_closed()
        await listener.close()


def test_public_pairing_settings_and_configuration_api(tmp_path, fake_adb, monkeypatch):
    import android_agent.app as app_module

    monkeypatch.setattr(app_module, "serial_ports", lambda: [{"port": "COM9"}])
    calls = []

    def provision(config, key, port):
        calls.append((config, key, port))
        return BOARD

    monkeypatch.setattr(app_module, "provision_board", provision)
    monkeypatch.setattr(UsbListener, "start", AsyncMock())
    with TestClient(create_app(RuntimeSettings(data_dir=tmp_path), fake_adb), base_url="http://127.0.0.1") as client:
        headers = {"X-Agent-CSRF": client.get("/api/session").json()["csrf"]}
        payload = {"port": "COM9", "ssid": "wifi", "password": "password123", "host": "192.168.1.20"}
        assert client.post("/api/usb/configure", json=payload).status_code == 403
        reply = client.post("/api/usb/configure", json=payload, headers=headers)
        assert reply.status_code == 200 and reply.json()["board_id"] == BOARD
        assert len(calls) == 1
        key = calls[0][1]
        assert len(key) == 64
        prefs = client.get("/api/settings").json()
        assert prefs["usb_pair_key_set"] and prefs["usb_board_id"] == BOARD
        assert "usb_pair_key" not in prefs
        assert key not in reply.text + json.dumps(prefs) + client.get("/api/status").text
        assert "password123" not in reply.text + json.dumps(prefs)
        assert ConfigStore(tmp_path).load().usb_pair_key.get_secret_value() == key
        assert client.post("/api/control/mode", json={"mode": "usb"}, headers=headers).status_code == 422
        assert client.post("/api/control/mode", json={"mode": "usb", "confirm_phone": True}, headers=headers).status_code == 409


def test_listener_start_failure_preserves_adb_workspace(tmp_path, fake_adb, monkeypatch):
    from pydantic import SecretStr

    prefs = Preferences(usb_enabled=True, usb_board_id=BOARD, usb_pair_key=SecretStr(KEY))
    ConfigStore(tmp_path).save(prefs)
    monkeypatch.setattr(UsbListener, "start", AsyncMock(side_effect=DeviceError("port unavailable")))
    with TestClient(create_app(RuntimeSettings(data_dir=tmp_path), fake_adb), base_url="http://127.0.0.1") as client:
        assert client.get("/api/status").status_code == 200
        assert client.get("/api/devices").json()["devices"][0]["serial"] == "phone1"
        assert client.get("/").status_code == 200


def test_usb_calibration_is_saved_separately(tmp_path, fake_adb):
    from types import SimpleNamespace

    with TestClient(create_app(RuntimeSettings(data_dir=tmp_path), fake_adb), base_url="http://127.0.0.1") as client:
        headers = {"X-Agent-CSRF": client.get("/api/session").json()["csrf"]}
        client.post("/api/devices/select", json={"serial": "phone1"}, headers=headers)
        bridge = SimpleNamespace(connected=True, hid_ready=True, board_id=BOARD, capabilities=["tap"],
                                 stop=AsyncMock(), close=AsyncMock())
        client.app.state.session.controller = UsbController(bridge, "phone1")
        reply = client.post("/api/control/calibrate", json={"phone": "phone1", "width": 200, "height": 400,
                                                          "counts_x": 800, "counts_y": 1200}, headers=headers)
        assert reply.status_code == 200
        prefs = client.get("/api/settings").json()
        assert f"{BOARD}:phone1" in prefs["usb_calibrations"]
        assert not prefs["ble_calibrations"]


async def test_listener_change_keeps_settings_saved_during_io(tmp_path, fake_adb, monkeypatch):
    import httpx

    app = create_app(RuntimeSettings(data_dir=tmp_path), fake_adb)
    started, release = asyncio.Event(), asyncio.Event()

    async def delayed_close():
        started.set()
        await release.wait()

    async with app.router.lifespan_context(app):
        monkeypatch.setattr(app.state.usb, "close", delayed_close)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://127.0.0.1") as client:
            headers = {"X-Agent-CSRF": app.state.csrf}
            operation = asyncio.create_task(client.post("/api/usb/listener", json={"enabled": False}, headers=headers))
            await asyncio.wait_for(started.wait(), 1)
            assert (await client.post("/api/settings", json={"actor": {"model": "new-model"}}, headers=headers)).status_code == 200
            release.set()
            assert (await operation).status_code == 200
            assert app.state.preferences.actor.model == "new-model"
            assert ConfigStore(tmp_path).load().actor.model == "new-model"


async def test_cancelled_configuration_finishes_matching_host_key(tmp_path, fake_adb, monkeypatch):
    import threading

    import httpx

    import android_agent.app as app_module

    started, release = threading.Event(), threading.Event()
    keys = []

    def delayed_configure(config, key, port):
        keys.append(key)
        started.set()
        assert release.wait(2)
        return BOARD

    monkeypatch.setattr(app_module, "serial_ports", lambda: [{"port": "COM9"}])
    monkeypatch.setattr(app_module, "provision_board", delayed_configure)
    monkeypatch.setattr(UsbListener, "start", AsyncMock())
    app = create_app(RuntimeSettings(data_dir=tmp_path), fake_adb)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://127.0.0.1") as client:
            operation = asyncio.create_task(client.post("/api/usb/configure", headers={"X-Agent-CSRF": app.state.csrf},
                json={"port": "COM9", "ssid": "test", "password": "password123", "host": "192.168.1.20"}))
            assert await asyncio.to_thread(started.wait, 1)
            operation.cancel()
            await asyncio.sleep(0.02)
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await operation
            await until(lambda: app.state.preferences.usb_board_id == BOARD)
            assert ConfigStore(tmp_path).load().usb_pair_key.get_secret_value() == keys[0]
