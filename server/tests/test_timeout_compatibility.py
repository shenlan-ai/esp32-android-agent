"""Exercise actual bounded-wait timeouts on all supported Python versions."""
import asyncio
import json

import pytest

import android_agent.app as app_module
import android_agent.usb as usb_module
from android_agent.app import create_app
from android_agent.async_utils import wait_for as bounded_wait
from android_agent.config import RuntimeSettings
from android_agent.errors import DeviceError
from android_agent.usb import UsbBridge, UsbListener


@pytest.fixture
def short_deadlines(monkeypatch):
    actual_wait_for = bounded_wait

    async def wait_for(awaitable, timeout):
        # Speed up only these production deadlines; keep the actual exception type.
        return await actual_wait_for(awaitable, .02 if timeout in {.5, 1, 3, 15} else timeout)

    monkeypatch.setattr(usb_module, "wait_for", wait_for)
    monkeypatch.setattr(app_module, "wait_for", wait_for)


class StalledWriter:
    def __init__(self):
        self.closed = False
        self.writes = []

    def is_closing(self):
        return self.closed

    def write(self, data):
        self.writes.append(data)

    async def drain(self):
        await asyncio.Event().wait()

    def close(self):
        self.closed = True

    async def wait_closed(self):
        await asyncio.Event().wait()


async def test_usb_drain_timeout_invalidates_without_replay(short_deadlines):
    writer = StalledWriter()
    bridge = UsbBridge(asyncio.StreamReader(), writer, "001122aabbcc")
    with pytest.raises(DeviceError, match="unknown"):
        await bridge._send({"op": "action", "action": "type", "text": "test"})
    assert len(writer.writes) == 1 and writer.closed and not bridge.connected
    with pytest.raises(DeviceError):
        await bridge._send({"op": "action", "action": "type", "text": "test"})
    assert len(writer.writes) == 1
    await asyncio.wait_for(bridge.close(), .4)


async def test_usb_close_timeout_returns_with_stalled_writer(short_deadlines):
    writer = StalledWriter()
    bridge = UsbBridge(asyncio.StreamReader(), writer, "001122aabbcc")
    await asyncio.wait_for(bridge.close(), .4)
    assert writer.closed and bridge._closing


async def test_silent_auth_timeout_finishes_owned_connection(short_deadlines):
    listener = UsbListener("127.0.0.1", 0)
    await listener.start("a" * 64, "001122aabbcc")
    reader, writer = await asyncio.open_connection("127.0.0.1", listener.port)
    try:
        challenge = json.loads(await reader.readline())
        assert challenge["op"] == "challenge"
        clients = list(listener._clients)
        assert len(clients) == 1
        assert await asyncio.wait_for(reader.read(), .4) == b""
        await asyncio.wait_for(clients[0], .4)
        assert not listener._clients and listener.current is None
    finally:
        writer.close()
        await writer.wait_closed()
        await listener.close()


async def test_sse_idle_heartbeat_keeps_subscription(tmp_path, fake_adb, short_deadlines):
    app = create_app(RuntimeSettings(data_dir=tmp_path), fake_adb)

    class Request:
        async def is_disconnected(self):
            return False

    async with app.router.lifespan_context(app):
        endpoint = next(route.endpoint for route in app.routes if getattr(route, "path", None) == "/api/events")
        iterator = (await endpoint(Request())).body_iterator
        try:
            assert "event: reset" in await anext(iterator)
            assert "heartbeat" in await anext(iterator)
            assert len(app.state.events.queues) == 1
            app.state.events.publish()
            assert "event: changed" in await anext(iterator)
        finally:
            await iterator.aclose()
        assert not app.state.events.queues


async def test_child_completion_cannot_swallow_caller_cancellation():
    child_done = asyncio.Event()

    async def caller():
        parent = asyncio.current_task()

        async def child():
            parent.cancel()
            child_done.set()
            return "must not escape cancellation"

        return await bounded_wait(child(), 1)

    task = asyncio.create_task(caller())
    with pytest.raises(asyncio.CancelledError):
        await task
    assert child_done.is_set() and task.cancelled()


@pytest.mark.parametrize("cancel", [False, True])
async def test_timeout_and_cancellation_finish_child_cleanup(cancel):
    started, finished = asyncio.Event(), asyncio.Event()

    async def child():
        try:
            started.set()
            await asyncio.Event().wait()
        finally:
            await asyncio.sleep(0)
            finished.set()

    task = asyncio.create_task(bounded_wait(child(), None if cancel else .02))
    await started.wait()
    if cancel:
        task.cancel()
    with pytest.raises(asyncio.CancelledError if cancel else asyncio.TimeoutError):
        await task
    assert finished.is_set()

async def test_bounded_wait_returns_result_and_preserves_exception():
    async def result():
        return 42

    async def failure():
        raise ValueError("child failure")

    assert await bounded_wait(result(), None) == 42
    with pytest.raises(ValueError, match="child failure"):
        await bounded_wait(failure(), 1)
