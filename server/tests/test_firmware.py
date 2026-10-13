"""Firmware integration with real manager/worker and memory-backed ROM only."""
import asyncio
import importlib.util
import json
import os
import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import pytest

from android_agent.app import create_app
from android_agent.ble import BleController
from android_agent.config import RuntimeSettings
from android_agent.errors import DeviceError
from android_agent.firmware import FirmwareManager, FirmwareTool
from android_agent.firmware_catalog import FirmwareCatalog
from android_agent.models import Action
from android_agent.screen import AdbScreen
from android_agent.session import DeviceSession

spec = importlib.util.spec_from_file_location(
    "firmware_fakes", Path(__file__).resolve().parents[2] / "scripts/tests/test_firmware_worker.py")
fakes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fakes)


class FakeTool:
    available = True

    def __init__(self, api=None):
        self.api = api or fakes.FakeApi()
        self.calls = []
        self.timeouts = []
        self.block = None
        self.started = asyncio.Event()
        self.gate = asyncio.Event()

    async def run(self, operation, *args, timeout=30):
        self.calls.append(operation)
        self.timeouts.append((operation, timeout))
        if operation == self.block:
            self.started.set()
            await self.gate.wait()
        try:
            result = fakes.worker.perform(fakes.worker.parser().parse_args([operation, *args]), self.api)
        except (OSError, ValueError) as exc:
            raise DeviceError(str(exc)) from exc
        return result


async def settle(manager):
    if manager.task:
        await asyncio.wait_for(asyncio.shield(manager.task), 5)
    return manager.public()["job"]


def manager_at(tmp_path, fake_adb, profile="esp32dev", *, clock=None):
    config = fakes.worker.PROFILES[profile]
    tool = FakeTool(fakes.FakeApi(config[1], config[3] * 1048576))
    settings = RuntimeSettings(data_dir=tmp_path / "data", firmware_dir=fakes.make_catalog(tmp_path / "catalog", profile))
    session = DeviceSession(fake_adb, AdbScreen(fake_adb))
    options = {"clock": clock} if clock else {}
    return FirmwareManager(settings, session, tool=tool, **options), settings


async def prepare(manager, profile="esp32dev"):
    manager.identify("DEMO-COM")
    identified = await settle(manager)
    assert identified["phase"] == "identified"
    manager.backup(identified["id"], profile)
    ready = await settle(manager)
    assert ready["phase"] == "ready"
    return ready


@pytest.mark.parametrize("profile", tuple(fakes.worker.PROFILES))
async def test_full_workflow_history_and_bound_rom(tmp_path, fake_adb, profile):
    manager, settings = manager_at(tmp_path, fake_adb, profile)
    ready = await prepare(manager, profile)
    expected_timeout = max(600, len(manager.tool.api.memory) / 8192 + 60)
    assert ("backup", expected_timeout) in manager.tool.timeouts
    original = bytes(manager.tool.api.memory)
    download, digest = await manager.download(ready["id"])
    assert download == original and digest == ready["backup"]["sha256"]
    assert ready["identity"]["pcb_model"] == "not_determined_from_chip_information"
    assert "mac" not in ready["identity"]
    manager.write(ready["id"], ready["confirmation"], True)
    written = await settle(manager)
    assert written["phase"] == "written" and written["image_verified"]
    assert not written["phone_input_verified"] and not written["confirmation"]
    assert (manager.tool.api.connections, manager.tool.api.write_calls, manager.tool.api.verify_calls) == (3, 1, 1)
    assert manager.session._maintenance is None
    assert (await manager.download(ready["id"]))[0] == original
    restarted = FirmwareManager(settings, manager.session, tool=manager.tool)
    await restarted.initialize()
    assert restarted.public()["job"] is None
    assert restarted.public()["backups"][0]["image_verified"]
    assert (await restarted.download(ready["id"]))[0] == original
    with pytest.raises(DeviceError):
        manager.write(ready["id"], ready["confirmation"], True)


@pytest.mark.parametrize("kind", ["false", "wrong", "expired"])
async def test_confirmation_refused_without_write(tmp_path, fake_adb, kind):
    now = [10.0]
    manager, _ = manager_at(tmp_path, fake_adb, clock=lambda: now[0])
    ready = await prepare(manager)
    if kind == "expired":
        now[0] += 300
        assert not manager.public()["job"]["confirmation"]
    with pytest.raises(DeviceError, match="confirmation"):
        manager.write(ready["id"], "bad" if kind == "wrong" else ready["confirmation"], kind != "false")
    assert manager.tool.api.write_calls == 0


@pytest.mark.parametrize("target", ["backup", "image", "manifest", "mac"])
async def test_integrity_or_changed_board_refused(tmp_path, fake_adb, target):
    manager, _ = manager_at(tmp_path, fake_adb)
    ready = await prepare(manager)
    stubs = manager.tool.api.stub_calls
    if target == "backup":
        (manager.directory / f"{ready['id']}.bin").write_bytes(b"short")
    elif target == "mac":
        manager.tool.api.mac = (1, 2, 3, 4, 5, 6)
    else:
        path = manager.jobs_dir / ready["id"] / "catalog"
        (path / ("manifest.json" if target == "manifest" else "esp32dev/firmware.bin")).write_bytes(b"changed")
    manager.write(ready["id"], ready["confirmation"], True)
    failed = await settle(manager)
    assert failed["phase"] == "failed" and not failed["confirmation"]
    assert manager.tool.api.write_calls == 0 and manager.tool.api.stub_calls == stubs
    with pytest.raises(DeviceError):
        manager.write(ready["id"], ready["confirmation"], True)


async def test_source_change_after_snapshot_does_not_change_write(tmp_path, fake_adb):
    manager, settings = manager_at(tmp_path, fake_adb)
    ready = await prepare(manager)
    (settings.firmware_dir / "esp32dev/firmware.bin").write_bytes(b"upstream changed")
    manager.write(ready["id"], ready["confirmation"], True)
    assert (await settle(manager))["phase"] == "written"


async def test_verification_failure_preserves_backup_without_replay(tmp_path, fake_adb):
    manager, _ = manager_at(tmp_path, fake_adb)
    ready = await prepare(manager)
    original = (await manager.download(ready["id"]))[0]
    manager.tool.api.fail_verify = True
    manager.write(ready["id"], ready["confirmation"], True)
    failed = await settle(manager)
    assert failed["phase"] == "failed" and not failed["image_verified"]
    assert not failed["confirmation"]
    assert manager.tool.api.write_calls == 1 and manager.tool.api.connections == 3
    assert (await manager.download(ready["id"]))[0] == original


async def test_short_backup_and_unsupported_capacity(tmp_path, fake_adb):
    manager, _ = manager_at(tmp_path, fake_adb)
    manager.identify("DEMO-COM")
    identified = await settle(manager)
    manager.tool.api.short_backup = True
    manager.backup(identified["id"], "esp32dev")
    assert (await settle(manager))["phase"] == "failed"
    assert not manager.backups and not manager.tool.api.write_calls
    manager.tool.api.flash_bytes = 16777216
    manager.identify("DEMO-COM")
    identified = await settle(manager)
    assert not identified["compatible"]
    with pytest.raises(DeviceError, match="matching"):
        manager.backup(identified["id"], "esp32dev")


@pytest.mark.parametrize("state", ["active", "paused", "hid", "usb", "lock"])
async def test_conflicting_control_blocks_maintenance(tmp_path, fake_adb, state):
    manager, _ = manager_at(tmp_path, fake_adb)
    session = manager.session
    if state in {"active", "paused"}:
        session._agent_owner, session._agent_running = object(), state == "active"
    elif state == "hid":
        session.controller = BleController(None, "phone1")
    elif state == "usb":
        manager.idle = lambda: False
    else:
        await session._lock.acquire()
    try:
        with pytest.raises(DeviceError):
            manager.identify("DEMO-COM")
        assert not manager.tool.calls
    finally:
        if state == "lock":
            session._lock.release()


async def test_queued_input_rechecks_maintenance(tmp_path, fake_adb):
    manager, _ = manager_at(tmp_path, fake_adb)
    await manager.session.select("phone1")
    await manager.session._lock.acquire()
    pending = asyncio.create_task(manager.session.execute(Action(action="home")))
    await asyncio.sleep(0)  # Let the input wait at the action lock.
    manager.session._lock.release()
    manager.tool.block = "identify"
    manager.identify("DEMO-COM")
    await manager.tool.started.wait()
    with pytest.raises(DeviceError, match="maintenance"):
        await pending
    assert not any("keyevent" in args for _, args in fake_adb.calls)
    await manager.cancel(manager.job["id"])


async def test_read_cancel_and_graceful_close_waits_write(tmp_path, fake_adb):
    manager, _ = manager_at(tmp_path, fake_adb)
    manager.tool.block = "identify"
    manager.identify("DEMO-COM")
    await manager.tool.started.wait()
    assert (await manager.cancel(manager.job["id"]))["job"]["phase"] == "cancelled"
    assert manager.session._maintenance is None
    manager.tool.block = None
    ready = await prepare(manager)
    manager.tool.block = "write"
    manager.tool.started.clear()
    manager.write(ready["id"], ready["confirmation"], True)
    await manager.tool.started.wait()
    with pytest.raises(DeviceError, match="cannot be cancelled"):
        await manager.cancel(ready["id"])
    closing = asyncio.create_task(manager.close())
    await asyncio.sleep(0)
    closing.cancel()
    await asyncio.sleep(0)
    assert not closing.done() and manager.busy
    manager.tool.gate.set()
    await asyncio.wait_for(closing, 5)
    assert manager.public()["job"]["phase"] == "written"


@asynccontextmanager
async def http_client(tmp_path, fake_adb, monkeypatch):
    manager, settings = manager_at(tmp_path, fake_adb)
    monkeypatch.setattr("android_agent.app.serial_ports", lambda: [{"port": "DEMO-COM"}])
    app = create_app(settings, fake_adb, firmware_factory=lambda runtime, session, idle:
                     FirmwareManager(runtime, session, idle, tool=manager.tool))
    async with app.router.lifespan_context(app), httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost") as client:
        client.headers["X-Agent-CSRF"] = (await client.get("/api/session")).json()["csrf"]
        yield client, app, app.state.firmware


async def test_http_validation_mutual_exclusion_and_stop(tmp_path, fake_adb, monkeypatch):
    async with http_client(tmp_path, fake_adb, monkeypatch) as (client, app, manager):
        assert (await client.post("/api/firmware/identify", json={"port": "COM5"})).status_code == 422
        assert (await client.post("/api/firmware/identify", json={"port": "DEMO-COM", "extra": 1})).status_code == 422
        assert (await client.post("/api/firmware/identify", headers={"X-Agent-CSRF": "bad"}, json={"port": "DEMO-COM"})).status_code == 403
        await client.post("/api/devices/select", json={"serial": "phone1"})
        ready = await prepare(manager)
        invalid = {"job_id": ready["id"], "confirmation": ready["confirmation"], "confirm_overwrite": "true"}
        assert (await client.post("/api/firmware/write", json=invalid)).status_code == 422
        manager.tool.block = "write"
        response = await client.post("/api/firmware/write", json={**invalid, "confirm_overwrite": True})
        assert response.status_code == 200
        await manager.tool.started.wait()
        for endpoint, payload in [("/api/action", {"action": "home"}),
                                  ("/api/devices/select", {"serial": "phone1"}),
                                  ("/api/control/mode", {"mode": "adb"}),
                                  ("/api/usb/listener", {"enabled": True}),
                                  ("/api/task/start", {"goal": "demo"})]:
            assert (await client.post(endpoint, json=payload)).status_code == 409, endpoint
        stopped = await asyncio.wait_for(client.post("/api/stop", json={}), 1)
        assert stopped.status_code == 200 and stopped.json()["firmware_in_progress"]
        assert manager.busy
        status = (await client.get("/api/status")).json()
        assert not status["capabilities"]
        download = await client.get(f"/api/firmware/backups/{ready['id']}")
        assert download.status_code == 200 and download.headers["x-firmware-sha256"] == ready["backup"]["sha256"]
        manager.tool.gate.set()
        assert (await settle(manager))["phase"] == "written"


async def test_http_cancel_does_not_cancel_owned_write(tmp_path, fake_adb, monkeypatch):
    # Cancel the response after write has started, as a disconnected browser does.
    manager, settings = manager_at(tmp_path, fake_adb)
    app = create_app(settings, fake_adb, firmware_factory=lambda runtime, session, idle:
                     FirmwareManager(runtime, session, idle, tool=manager.tool))
    delivered = asyncio.Event()
    response_gate = asyncio.Event()

    @app.middleware("http")
    async def delayed_response(request, call_next):
        response = await call_next(request)
        if request.url.path == "/api/firmware/write":
            delivered.set()
            await response_gate.wait()
        return response

    async with app.router.lifespan_context(app), httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost") as client:
        client.headers["X-Agent-CSRF"] = (await client.get("/api/session")).json()["csrf"]
        manager = app.state.firmware
        ready = await prepare(manager)
        manager.tool.block = "write"
        pending = asyncio.create_task(client.post("/api/firmware/write", json={
            "job_id": ready["id"], "confirmation": ready["confirmation"], "confirm_overwrite": True}))
        await delivered.wait()
        await manager.tool.started.wait()
        pending.cancel()
        with pytest.raises(asyncio.CancelledError):
            await pending
        assert (await client.get("/api/firmware")).json()["job"]["phase"] == "writing"
        manager.tool.gate.set()
        assert (await settle(manager))["phase"] == "written"


@pytest.mark.parametrize("mutation", ["bool", "duplicate", "layout"])
def test_catalog_rejects_untrusted_manifest(tmp_path, mutation):
    folder = fakes.make_catalog(tmp_path / "catalog")
    path = folder / "manifest.json"
    data = json.loads(path.read_text())
    if mutation == "bool":
        data["schema"] = True
    elif mutation == "layout":
        data["profiles"][0]["images"][0]["offset"] = 0
    path.write_text('{"schema":1,"schema":1,"profiles":[]}' if mutation == "duplicate" else json.dumps(data))
    with pytest.raises(ValueError):
        FirmwareCatalog(folder).validate("esp32dev")


@pytest.mark.parametrize("cancel", [False, True])
async def test_subprocess_timeout_or_cancel_stops_own_tree(tmp_path, cancel):
    script = tmp_path / "blocking.py"
    pidfile = tmp_path / "child.pid"
    script.write_text("import subprocess,sys,time\nfrom pathlib import Path\n"
                      "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'])\n"
                      "Path(sys.argv[2]).write_text(str(child.pid))\n"
                      "print('started',flush=True)\ntime.sleep(60)\n")
    tool = FirmwareTool(RuntimeSettings(data_dir=tmp_path))
    tool.command = [sys.executable, str(script)]
    running = asyncio.create_task(tool.run("diagnose", str(pidfile), timeout=2))
    try:
        child_pid = None
        for _ in range(100):
            content = pidfile.read_text().strip() if pidfile.exists() else ""
            if content.isdecimal() and int(content) > 0:
                child_pid = int(content)
                break
            await asyncio.sleep(.01)
        assert child_pid is not None, "Child did not publish a complete PID"
        if cancel:
            running.cancel()
        with pytest.raises(asyncio.CancelledError if cancel else DeviceError):
            await asyncio.wait_for(running, 15)
    finally:
        running.cancel()
        await asyncio.gather(running, return_exceptions=True)
    if os.name == "nt":
        result = subprocess.run([str(Path(os.environ["SystemRoot"]) / "System32/tasklist.exe"),
                                 "/FI", f"PID eq {child_pid}", "/FO", "CSV", "/NH"],
                                capture_output=True, timeout=10, check=True)
        assert f'"{child_pid}"'.encode() not in result.stdout
    else:
        try:
            os.kill(child_pid, 0)
        except ProcessLookupError:
            return
        assert Path(f"/proc/{child_pid}/stat").read_text().split()[2] == "Z"


@pytest.mark.parametrize("mutation", [None, "old", "bool", "operation", "stage", "reason", "count",
                                      "total", "malformed", "overflow", "zero"])
async def test_failed_subprocess_diagnostics_are_strict_and_private(tmp_path, mutation):
    secret = "private-key-device-and-path"
    payload = {"ok": False, "protocol": "android-agent-firmware-v1", "error": "operation_failed",
               "operation": "backup", "failure": {"stage": "read", "reason": "packet_transfer_stopped",
               "completed_bytes": 262144, "total_bytes": 4194304, "extra": secret}, "extra": secret}
    if mutation == "old":
        payload.pop("failure")
    elif mutation == "bool":
        payload["ok"] = 0
    elif mutation == "operation":
        payload["operation"] = "write"
    elif mutation in {"stage", "reason"}:
        payload["failure"][mutation] = secret
    elif mutation == "count":
        payload["failure"]["completed_bytes"] = True
    elif mutation == "total":
        payload["failure"]["total_bytes"] = 1
    output = (secret if mutation == "malformed" else
              secret * 7000 if mutation == "overflow" else json.dumps(payload))
    script = tmp_path / "failed.py"
    count = tmp_path / "calls.txt"
    script.write_text("import sys\nfrom pathlib import Path\n"
                      f"p=Path({str(count)!r})\np.write_text(p.read_text()+'x' if p.exists() else 'x')\n"
                      f"print({output!r})\nprint({secret!r},file=sys.stderr)\n"
                      f"sys.exit({0 if mutation == 'zero' else 1})\n")
    tool = FirmwareTool(RuntimeSettings(data_dir=tmp_path))
    tool.command = [sys.executable, str(script)]
    with pytest.raises(DeviceError) as raised:
        await tool.run("backup", timeout=5)
    message = str(raised.value)
    assert "no Flash was written" in message
    assert secret not in message
    if mutation is None:
        assert "Flash reading (262144/4194304 bytes completed): transfer stopped" in message
    else:
        assert "bytes completed" not in message and "during Flash reading" not in message
    assert count.read_text() == "x"  # A failed process is never replayed.


@pytest.mark.parametrize("operation", ["backup", "write"])
async def test_subprocess_timeout_message_distinguishes_read_only_and_write(tmp_path, operation):
    script = tmp_path / "slow.py"
    script.write_text("import time\ntime.sleep(60)\n")
    tool = FirmwareTool(RuntimeSettings(data_dir=tmp_path))
    tool.command = [sys.executable, str(script)]
    with pytest.raises(DeviceError) as raised:
        await tool.run(operation, timeout=.2)
    assert "timed out" in str(raised.value)
    assert ("no Flash was written" in str(raised.value)) is (operation == "backup")
    assert ("Keep the backup" in str(raised.value)) is (operation == "write")


async def test_failed_write_verification_keeps_result_uncertain(tmp_path):
    payload = {"ok": False, "protocol": "android-agent-firmware-v1", "error": "operation_failed",
               "operation": "write", "failure": {"stage": "verify", "reason": "digest_mismatch"}}
    script = tmp_path / "verify.py"
    script.write_text(f"import sys\nprint({json.dumps(payload)!r})\nsys.exit(1)\n")
    tool = FirmwareTool(RuntimeSettings(data_dir=tmp_path))
    tool.command = [sys.executable, str(script)]
    with pytest.raises(DeviceError) as raised:
        await tool.run("write", timeout=5)
    assert "read-back verification: digest mismatch" in str(raised.value)
    assert "Keep the backup" in str(raised.value) and "no Flash was written" not in str(raised.value)
