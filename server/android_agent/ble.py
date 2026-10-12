from __future__ import annotations

import asyncio
import json
import time
from typing import Literal

import serial
from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator
from serial.tools import list_ports

from .errors import DeviceError
from .models import Action
from .screen import Frame

PROTOCOL = 1
KEYS = {"enter", "backspace", "esc", "tab", "space", "up", "down", "left", "right"}
CAPABILITIES = {"tap", "swipe", "long_press", "scroll", "type", "key", "wait"}


def serial_ports() -> list[dict]:
    return [
        {"port": port.device, "description": port.description, "vid": port.vid, "pid": port.pid}
        for port in list_ports.comports()
        if port.vid in {0x10C4, 0x1A86, 0x303A, 0x0403, 0x2886}
    ]


class Calibration(BaseModel):
    model_config = ConfigDict(extra="forbid")
    phone: str = Field(min_length=1, max_length=200)
    width: StrictInt = Field(ge=1, le=20000)
    height: StrictInt = Field(ge=1, le=20000)
    counts_x: StrictInt = Field(ge=100, le=4000)
    counts_y: StrictInt = Field(ge=100, le=4000)

    def check(self, frame: Frame) -> None:
        if (self.phone, self.width, self.height) != (frame.serial, frame.width, frame.height):
            raise DeviceError("Phone or screen orientation changed; calibrate this screen again")

    def point(self, x: int, y: int) -> tuple[int, int]:
        return round(x * self.counts_x / 1000), round(y * self.counts_y / 1000)


class BridgeSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["adb", "ble", "usb"]
    port: str | None = Field(None, max_length=200)
    confirm_phone: bool = False

    @model_validator(mode="after")
    def confirm_binding(self):
        if self.mode != "adb" and not self.confirm_phone:
            raise ValueError("Confirm that this HID board controls the selected phone")
        return self


class PointerProbe(BaseModel):
    model_config = ConfigDict(extra="forbid")
    x: StrictInt = Field(ge=0, le=4000)
    y: StrictInt = Field(ge=0, le=4000)


class SerialBridge:
    """One reader owns serial input. Each action is written exactly once."""

    def __init__(self, port: str, factory=serial.Serial):
        self.port = port
        self.factory = factory
        self.device = None
        self.session = ""
        self.ble_connected = False
        self.capabilities: list[str] = []
        self.firmware = ""
        self._next_id = 0
        self._pending: dict[int, asyncio.Future] = {}
        self._write_lock = asyncio.Lock()
        self._reader: asyncio.Task | None = None
        self._heartbeat: asyncio.Task | None = None
        self._error: str | None = None
        self._closing = False
        self._last_heartbeat = 0.0

    ready_field = "ble_connected"

    @property
    def hid_ready(self) -> bool:
        return self.ble_connected

    @property
    def connected(self) -> bool:
        return bool(self.session and not self._error and not self._closing)

    def public(self) -> dict:
        return {
            "port": self.port,
            "connected": self.connected,
            "ble_connected": self.ble_connected,
            "hid_ready": self.hid_ready,
            "firmware": self.firmware,
            "ble_name": "Android Agent BLE",
            "error": self._error,
        }

    async def open(self) -> None:
        try:
            self.device = self.factory(port=None, baudrate=115200, timeout=0.1, write_timeout=0.5)
            self.device.dtr = False
            self.device.rts = False
            self.device.port = self.port
            await asyncio.to_thread(self.device.open)
            # UART bridges may reset ESP32 on opening. Wait before starting watchdog.
            await asyncio.sleep(1.5)
            await asyncio.to_thread(self.device.reset_input_buffer)
            self._reader = asyncio.create_task(self._read())
            result = await self.request("hello", timeout=5)
            if result.get("status") != "hello" or result.get("chip") != "esp32":
                raise DeviceError("Install the classic ESP32 BLE bridge firmware before connecting")
            self.session = result["session"]
            caps = result.get("capabilities")
            if not isinstance(caps, list) or not all(isinstance(cap, str) for cap in caps):
                raise DeviceError("Invalid bridge capabilities")
            self.capabilities = sorted(CAPABILITIES.intersection(caps))
            self.firmware = str(result.get("firmware", "unknown"))[:50]
            self._last_heartbeat = time.monotonic()
            self._heartbeat = asyncio.create_task(self._pulse())
        except (OSError, serial.SerialException) as exc:
            await self.close()
            raise DeviceError(
                "Cannot open board serial port; close other serial tools and retry"
            ) from exc
        except BaseException:
            await self.close()
            raise

    def _fail(self, message: str) -> None:
        if self._error:
            return
        self._error = message
        self.ble_connected = False
        for future in tuple(self._pending.values()):
            if not future.done():
                future.set_exception(DeviceError(message))

    def _receive(self, line: bytes) -> None:
        try:
            response = json.loads(line)
        except (ValueError, UnicodeDecodeError):
            return  # UART boot messages are not protocol responses.
        if (not isinstance(response, dict) or type(response.get("v")) is not int
                or response["v"] != PROTOCOL):
            return
        incoming_session = response.get("session")
        if self.session and incoming_session != self.session:
            self._fail("Board session changed; reconnect before controlling")
            return
        if not self.session and (not isinstance(incoming_session, str)
                                 or len(incoming_session) != 32):
            return
        if type(response.get(self.ready_field)) is not bool:
            self._fail("Invalid HID connection state")
            return
        self.ble_connected = response[self.ready_field]
        if response.get("status") == "heartbeat":
            self._last_heartbeat = time.monotonic()
        if response.get("error") in {"stale_session", "heartbeat_expired", "ble_disconnected",
                                     "usb_disconnected", "hid_report_failed"}:
            self._fail("HID report was not submitted; check the phone and reconnect"
                       if response.get("error") == "hid_report_failed"
                       else "Board or phone disconnected; reconnect before controlling")
            return
        if response.get("status") in {"accepted", "running"}:
            return
        command_id = response.get("id")
        future = self._pending.get(command_id) if type(command_id) is int else None
        if future and not future.done():
            future.set_result(response)

    async def _read(self) -> None:
        buffer = bytearray()
        try:
            while not self._closing:
                chunk = await asyncio.to_thread(self.device.read, 256)
                buffer.extend(chunk)
                while b"\n" in buffer:
                    line, _, rest = buffer.partition(b"\n")
                    buffer = bytearray(rest)
                    if len(line) > 1024:
                        self._fail("Oversized bridge response; reconnect the board")
                        return
                    self._receive(line)
                    if self._error:
                        return
                if len(buffer) > 1024:
                    self._fail("Oversized bridge response; reconnect the board")
                    return
        except (OSError, serial.SerialException):
            self._fail("Board serial connection lost; reconnect before controlling")

    async def _send(self, payload: dict) -> None:
        if self._error or self._closing or not self.device:
            raise DeviceError(self._error or "Board serial connection is closed")
        data = (json.dumps(payload, ensure_ascii=True, separators=(",", ":")) + "\n").encode()
        if len(data) > 1024:
            raise DeviceError("Bridge command is too large")
        try:
            async with self._write_lock:
                write = asyncio.create_task(asyncio.to_thread(self.device.write, data))
                try:
                    written = await asyncio.shield(write)
                except asyncio.CancelledError:
                    # Finish the bounded physical write before another request can write.
                    await write
                    raise
                if written != len(data):
                    raise serial.SerialTimeoutException("short write")
        except (OSError, serial.SerialException) as exc:
            self._fail(
                "Board write failed; action result is unknown, reconnect and observe the phone"
            )
            raise DeviceError(self._error) from exc

    async def request(self, op: str, timeout: float = 30, **args) -> dict:
        self._next_id += 1
        command_id = self._next_id
        future = asyncio.get_running_loop().create_future()
        self._pending[command_id] = future
        try:
            await self._send(
                {"v": PROTOCOL, "session": self.session, "id": command_id, "op": op, **args}
            )
            try:
                result = await asyncio.wait_for(future, timeout)
            except TimeoutError as exc:
                self._fail(
                    "Board timeout; action result is unknown, reconnect and observe the phone"
                )
                raise DeviceError(self._error) from exc
            if result.get("status") == "error":
                raise DeviceError(
                    "Bridge rejected the command; check pairing, arguments and firmware"
                )
            if result.get("status") == "cancelled":
                raise DeviceError("Board action cancelled")
            expected = {"hello": "hello", "stop": "stopped", "status": "ready", "action": "done"}
            if result.get("status") != expected.get(op):
                self._fail("Unexpected bridge result; reconnect and observe the phone")
                raise DeviceError(self._error)
            return result
        except asyncio.CancelledError:
            if op == "action" and self.connected:
                await asyncio.shield(self.stop())
            raise
        finally:
            self._pending.pop(command_id, None)
            if not future.done():
                future.cancel()
            elif not future.cancelled():
                future.exception()  # Consume failures if serial write also failed.

    async def _pulse(self) -> None:
        try:
            while self.connected:
                if time.monotonic() - self._last_heartbeat > 2:
                    self._fail(
                        "Board heartbeat lost; action result is unknown, reconnect and observe"
                    )
                    return
                await self._send({"v": 1, "session": self.session, "id": 0, "op": "heartbeat"})
                await asyncio.sleep(0.5)
        except DeviceError:
            pass

    async def stop(self) -> dict:
        if not self.connected:
            return {"cancelled": True, "release": "unconfirmed_board_watchdog_release"}
        try:
            result = await self.request("stop", timeout=2)
            return {
                "cancelled": True,
                "release": "hid_release_sent"
                if result[self.ready_field] and result.get("release_sent") is True
                else "unconfirmed_hid_release"
                if result[self.ready_field]
                else "board_state_cleared_phone_disconnected",
            }
        except DeviceError:
            return {"cancelled": True, "release": "unconfirmed_board_watchdog_release"}

    async def close(self) -> None:
        if self._closing:
            return
        if self.connected:
            await self.stop()
        self._closing = True
        tasks = [task for task in (self._heartbeat, self._reader) if task]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self._fail("Board serial connection is closed")
        if self.device:
            await asyncio.to_thread(self.device.close)


class BleController:
    mode = "ble"

    def __init__(self, bridge: SerialBridge, phone: str, calibration: Calibration | None = None):
        self.bridge = bridge
        self.phone = phone
        self.calibration = calibration

    @property
    def capabilities(self) -> list[str]:
        if not self.bridge.connected or not self.bridge.hid_ready:
            return []
        caps = self.bridge.capabilities
        if not self.calibration:
            return [cap for cap in caps if cap in {"type", "key", "wait"}]
        return caps

    async def execute(self, action: Action, frame: Frame) -> dict:
        if action.action not in self.capabilities:
            raise DeviceError(
                "HID action unavailable; check board connection, phone binding and calibration"
            )
        if frame.serial != self.phone:
            raise DeviceError("HID board is bound to a different phone")
        name = action.action
        args = {"action": name}
        if name in {"tap", "long_press", "swipe", "scroll"}:
            if not self.calibration:
                raise DeviceError("Calibrate the HID mouse before coordinate actions")
            self.calibration.check(frame)
            start = (action.x1, action.y1) if name == "swipe" else (action.x, action.y)
            args["x"], args["y"] = self.calibration.point(*start)
            if name == "swipe":
                args["x2"], args["y2"] = self.calibration.point(action.x2, action.y2)
            if name in {"swipe", "long_press"}:
                args["duration_ms"] = action.duration_ms
            if name == "scroll":
                args["lines"] = action.lines
        elif name == "type":
            args["text"] = action.text
        elif name == "key":
            if action.key not in KEYS:
                raise DeviceError("This Android navigation/media key has not been verified for HID")
            args["key"] = action.key
        else:
            args["duration_ms"] = action.duration_ms
        result = await self.bridge.request("action", **args)
        return {
            key: value
            for key in ("elapsed_ms", "button_held_ms")
            if type(value := result.get(key)) is int and 0 <= value <= 60000
        }

    async def locate(self, probe: PointerProbe) -> dict:
        if not self.bridge.connected or not self.bridge.hid_ready:
            raise DeviceError("Connect the HID board to the phone first")
        await self.bridge.request("action", action="locate", x=probe.x, y=probe.y)
        return {"ok": True}

    async def stop(self) -> dict:
        return await self.bridge.stop()

    async def close(self) -> None:
        await self.bridge.close()
