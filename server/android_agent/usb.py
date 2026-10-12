from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import re
import secrets
import time

from .async_utils import wait_for
from .ble import CAPABILITIES, BleController, SerialBridge
from .errors import DeviceError

BOARD_ID = re.compile(r"^[0-9a-f]{12}$")


def authentication_proof(key: str, nonce: str, board: str) -> str:
    message = f"android-agent-usb-v1:{nonce}:{board}".encode("ascii")
    return hmac.new(key.encode("ascii"), message, hashlib.sha256).hexdigest()


class UsbBridge(SerialBridge):
    """Authenticated TCP transport; shares exactly-once requests and HID mapping with BLE."""

    ready_field = "usb_connected"

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, board_id: str):
        super().__init__("")
        self.stream, self.writer, self.board_id = reader, writer, board_id
        self.profile = ""

    def public(self) -> dict:
        return {"connected": self.connected, "hid_ready": self.hid_ready,
                "usb_connected": self.hid_ready, "firmware": self.firmware,
                "board_id": self.board_id, "profile": self.profile, "error": self._error}

    async def open(self) -> None:
        if self._reader:
            if not self.connected:
                raise DeviceError("USB board connection expired; bind the new connection explicitly")
            return
        self._reader = asyncio.create_task(self._read())
        try:
            result = await self.request("hello", timeout=3)
            if result.get("chip") != "esp32s3" or result.get("board_id") != self.board_id:
                raise DeviceError("USB board identity changed; provision the S3 firmware again")
            caps = result.get("capabilities")
            if not isinstance(caps, list) or not all(isinstance(cap, str) for cap in caps):
                raise DeviceError("Invalid USB board capabilities")
            self.capabilities = sorted(CAPABILITIES.intersection(caps))
            self.session = result["session"]
            self.firmware = str(result.get("firmware", "unknown"))[:50]
            self.profile = str(result.get("profile", "unknown"))[:60]
            self._last_heartbeat = time.monotonic()
            self._heartbeat = asyncio.create_task(self._pulse())
        except BaseException:
            await self.close()
            raise

    def _fail(self, message: str) -> None:
        super()._fail(message)
        self.writer.close()  # Tell firmware to release immediately; watchdog is the fallback.

    async def _read(self) -> None:
        try:
            while not self._closing:
                line = await self.stream.readline()
                if not line:
                    self._fail("USB board network connection lost; reconnect and observe the phone")
                    return
                if len(line) > 1024 or not line.endswith(b"\n"):
                    self._fail("Oversized USB board response; reconnect the board")
                    return
                self._receive(line)
                if self._error:
                    return
        except (OSError, ValueError):
            self._fail("Invalid USB board stream; reconnect and observe the phone")

    async def _send(self, payload: dict) -> None:
        if self._error or self._closing or self.writer.is_closing():
            raise DeviceError(self._error or "USB board network connection is closed")
        data = (json.dumps(payload, ensure_ascii=True, separators=(",", ":")) + "\n").encode()
        if len(data) > 1024:
            raise DeviceError("Bridge command is too large")
        try:
            async with self._write_lock:
                self.writer.write(data)
                await wait_for(self.writer.drain(), 0.5)
        except (OSError, asyncio.TimeoutError) as exc:
            self._fail("USB board write failed; action result is unknown, reconnect and observe")
            raise DeviceError(self._error) from exc

    async def close(self) -> None:
        if self._closing:
            return
        if self.connected:
            await self.stop()
        self._closing = True
        tasks = [task for task in (self._heartbeat, self._reader)
                 if task and task is not asyncio.current_task()]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self._fail("USB board network connection is closed")
        try:
            await wait_for(self.writer.wait_closed(), 1)
        except (OSError, asyncio.TimeoutError):
            pass


class UsbController(BleController):
    mode = "usb"


class UsbListener:
    def __init__(self, host: str, port: int):
        self.host, self.port = host, port
        self.server = None
        self.current: UsbBridge | None = None
        self.board_id = ""
        self._key = ""
        self.error = None
        self._clients: set[asyncio.Task] = set()
        self._lock = asyncio.Lock()
        self._start_lock = asyncio.Lock()
        self._accepting = False

    def public(self) -> dict:
        return {"listening": self.server is not None, "port": self.port,
                "paired_board": self.board_id or None, "error": self.error,
                "board": self.current.public() if self.current else None}

    async def start(self, key: str, board_id: str) -> None:
        async with self._start_lock:
            if not re.fullmatch(r"[0-9a-f]{64}", key) or not BOARD_ID.fullmatch(board_id):
                self.error = "Provision an ESP32-S3 USB board before enabling its listener"
                raise DeviceError(self.error)
            if self.server and (key, board_id) == (self._key, self.board_id):
                return
            await self.close()
            self._key, self.board_id, self.error = key, board_id, None
            try:
                self._accepting = True
                self.server = await asyncio.start_server(self._accept, self.host, self.port,
                                                         limit=1024, backlog=8)
                self.port = self.server.sockets[0].getsockname()[1]
            except OSError as exc:
                self._accepting = False
                self.error = "USB board port unavailable; close the other listener or change its port"
                raise DeviceError(self.error) from exc

    async def _accept(self, reader, writer) -> None:
        task = asyncio.current_task()
        if not self._accepting or len(self._clients) >= 8:
            writer.close()
            return
        self._clients.add(task)
        bridge = None
        try:
            nonce = secrets.token_hex(32)
            writer.write((json.dumps({"v": 1, "op": "challenge", "nonce": nonce}) + "\n").encode())
            await wait_for(writer.drain(), 0.5)
            line = await wait_for(reader.readline(), 3)
            if not line.endswith(b"\n") or len(line) > 1024:
                return
            auth = json.loads(line)
            if (not isinstance(auth, dict) or type(auth.get("v")) is not int or auth["v"] != 1
                    or auth.get("op") != "authenticate" or auth.get("board_id") != self.board_id
                    or not isinstance(auth.get("proof"), str)
                    or not secrets.compare_digest(auth["proof"],
                                                   authentication_proof(self._key, nonce, self.board_id))):
                return
            if self._lock.locked():
                return  # Bound handshake time instead of queuing credential holders.
            async with self._lock:
                if self.current and self.current.connected:
                    return
                if self.current:
                    await self.current.close()
                bridge = UsbBridge(reader, writer, self.board_id)
                await bridge.open()
                self.current = bridge
            # Own the socket lifecycle even when no controller is selected.
            await bridge._reader
        except (OSError, ValueError, asyncio.TimeoutError, DeviceError):
            pass  # Do not log attacker-controlled data or authentication material.
        finally:
            try:
                if bridge:
                    await bridge.close()
                else:
                    writer.close()
                    try:
                        await wait_for(writer.wait_closed(), 1)
                    except (OSError, asyncio.TimeoutError):
                        pass
            finally:
                self._clients.discard(task)

    async def close(self) -> None:
        self._accepting = False
        server = self.server
        if self.server:
            self.server.close()
            self.server = None
        if self.current:
            await self.current.close()
            self.current = None
        clients = tuple(self._clients)
        for task in clients:
            task.cancel()
        await asyncio.gather(*clients, return_exceptions=True)
        if server:
            # New Python versions wait for accepted sockets as well as the listening socket.
            await server.wait_closed()
