from __future__ import annotations

import ipaddress
import json
import re
import time

import serial
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from .errors import DeviceError
from .usb import BOARD_ID


class UsbProvision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    port: str = Field(min_length=1, max_length=200)
    ssid: str = Field(min_length=1, max_length=32)
    password: SecretStr
    host: str

    @field_validator("ssid")
    @classmethod
    def ssid_length(cls, value):
        if len(value.encode("utf-8")) > 32 or any(ord(c) < 32 for c in value):
            raise ValueError("Wi-Fi SSID must be at most 32 UTF-8 bytes without control characters")
        return value

    @field_validator("password")
    @classmethod
    def password_length(cls, value):
        text = value.get_secret_value()
        if text and (not 8 <= len(text.encode("utf-8")) <= 63 or any(ord(c) < 32 for c in text)):
            raise ValueError("Wi-Fi password must be empty for open networks or 8-63 UTF-8 bytes")
        return value

    @field_validator("host")
    @classmethod
    def host_address(cls, value):
        address = ipaddress.IPv4Address(value)
        if address.is_loopback or address.is_multicast or address.is_unspecified or address.is_reserved:
            raise ValueError("Use the computer's LAN IPv4 address reachable by the board")
        return str(address)


def provision_board(config: UsbProvision, key: str, service_port: int, factory=serial.Serial) -> str:
    """Bounded worker; only configuration goes over CDC, never HID actions."""
    if not re.fullmatch(r"[0-9a-f]{64}", key) or not 1 <= service_port <= 65535:
        raise DeviceError("Invalid USB listener settings")
    device = None
    try:
        device = factory(port=None, baudrate=115200, timeout=0.1, write_timeout=0.5)
        device.dtr = False
        device.rts = False
        device.port = config.port
        device.open()
        time.sleep(1.5)
        device.reset_input_buffer()

        def exchange(command):
            data = (json.dumps(command, ensure_ascii=True, separators=(",", ":")) + "\n").encode()
            if len(data) > 1024 or device.write(data) != len(data):
                raise DeviceError("USB configuration write failed; reconnect the board and retry")
            deadline = time.monotonic() + 3
            buffer = bytearray()
            while time.monotonic() < deadline:
                buffer.extend(device.read_until(b"\n", size=1025))
                if len(buffer) > 1024:
                    raise DeviceError("Invalid USB configuration response")
                if not buffer.endswith(b"\n"):
                    continue
                line = bytes(buffer)
                buffer.clear()
                try:
                    result = json.loads(line)
                except (ValueError, UnicodeDecodeError):
                    continue
                if (isinstance(result, dict) and type(result.get("v")) is int and result["v"] == 1
                        and type(result.get("id")) is int and result["id"] == command["id"]):
                    return result
            raise DeviceError("USB configuration timeout; use the native USB port with S3 firmware")

        identity = exchange({"v": 1, "id": 1, "op": "get_config"})
        board = identity.get("board_id", "")
        if (identity.get("chip") != "esp32s3" or identity.get("status") != "config"
                or identity.get("protocol") != "android-agent-usb-v1"
                or not isinstance(board, str) or not BOARD_ID.fullmatch(board)):
            raise DeviceError("Selected port is not the ESP32-S3 USB bridge; no configuration was written")
        result = exchange({"v": 1, "id": 2, "op": "configure", "ssid": config.ssid,
                           "password": config.password.get_secret_value(), "host": config.host,
                           "port": service_port, "token": key})
        if result.get("status") != "configured" or result.get("board_id") != board:
            raise DeviceError("Board did not confirm configuration; reconnect and check it before retrying")
        return board
    except (OSError, serial.SerialException) as exc:
        raise DeviceError("Cannot configure USB board; close serial tools and use its native USB port") from exc
    finally:
        if device:
            device.close()
