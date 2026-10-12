from __future__ import annotations

import asyncio
import ipaddress
import re
import shlex
import shutil
from pathlib import Path

from .errors import DeviceError
from .models import DeviceInfo


def validate_address(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9._-]+:[0-9]{1,5}", value):
        raise ValueError("Use host:port (pairing and connection ports are different)")
    host, port = value.rsplit(":", 1)
    if not 1 <= int(port) <= 65535 or len(host) > 253 or host.startswith("-"):
        raise ValueError("Invalid host or port")
    if host.replace(".", "").isdigit():
        ipaddress.IPv4Address(host)
    return value


class AdbClient:
    def __init__(self, executable: str = "adb", timeout: float = 10):
        self.executable = executable
        self.timeout = timeout
        self._processes: set[asyncio.subprocess.Process] = set()

    @property
    def available(self) -> bool:
        return bool(shutil.which(self.executable) or Path(self.executable).is_file())

    async def run(
        self, *args: str, serial: str | None = None, timeout: float | None = None
    ) -> bytes:
        if not self.available:
            raise DeviceError("ADB not found. Install Android Platform Tools or set ADB_PATH.")
        command = [self.executable, *(["-s", serial] if serial else []), *args]
        try:
            proc = await asyncio.create_subprocess_exec(
                *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
        except OSError as exc:
            raise DeviceError("Could not start ADB; check the tool path and permissions") from exc
        self._processes.add(proc)
        try:
            out, err = await asyncio.wait_for(proc.communicate(), timeout or self.timeout)
            if proc.returncode:
                # Arguments may contain text or pairing credentials: never echo the command.
                detail = err.decode("utf-8", errors="replace").strip()[:300]
                if args and args[0] == "pair":
                    detail = "Pairing failed; check the pairing address and code on the phone"
                raise DeviceError(detail or "ADB operation failed")
            if len(out) > 32 * 1024 * 1024:
                raise DeviceError("ADB output exceeded the size limit")
            return out
        except asyncio.TimeoutError as exc:
            raise DeviceError(
                "ADB timed out. The operation may have run; inspect the screen before retrying."
            ) from exc
        finally:
            self._processes.discard(proc)
            if proc.returncode is None:
                proc.kill()
                await proc.communicate()

    async def shell(self, serial: str, *args: str) -> bytes:
        # adb shell concatenates its arguments on the remote device.
        return await self.run("shell", *[shlex.quote(str(arg)) for arg in args], serial=serial)

    async def devices(self) -> list[DeviceInfo]:
        output = (await self.run("devices", "-l")).decode("utf-8", errors="replace")
        devices = []
        for line in output.splitlines():
            fields = line.split()
            if len(fields) < 2 or line.startswith(("List of devices", "*")):
                continue
            serial, state = fields[:2]
            metadata = dict(part.split(":", 1) for part in fields[2:] if ":" in part)
            devices.append(
                DeviceInfo(
                    serial=serial,
                    state=state,
                    model=metadata.get("model", ""),
                    transport="wireless" if ":" in serial or "_adb-tls" in serial else "usb",
                )
            )
        return devices

    async def pair(self, address: str, code: str) -> None:
        validate_address(address)
        if not re.fullmatch(r"\d{6}", code):
            raise ValueError("Pairing code must contain six digits")
        result = (await self.run("pair", address, code, timeout=20)).decode(errors="replace")
        if "successfully paired" not in result.lower():
            raise DeviceError("Pairing failed; verify the pairing address and six-digit code")

    async def connect(self, address: str) -> None:
        validate_address(address)
        result = (await self.run("connect", address)).decode(errors="replace").lower()
        if "connected to" not in result:
            raise DeviceError(
                "Connection failed; use the connection port shown under Wireless debugging"
            )

    async def discover(self) -> list[dict]:
        text = (await self.run("mdns", "services")).decode(errors="replace")
        services = []
        for line in text.splitlines():
            fields = line.split()
            if len(fields) >= 3 and "_adb-tls-" in fields[1]:
                services.append({"name": fields[0], "kind": fields[1], "address": fields[2]})
        return services

    async def stop(self) -> None:
        for proc in tuple(self._processes):
            if proc.returncode is None:
                proc.kill()

    async def close(self) -> None:
        await self.stop()
