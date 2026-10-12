"""Identify an ESP chip without erasing or writing flash."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys

USB_BRIDGES = re.compile(r"USB\\VID_(?:10C4|1A86|303A|0403)", re.I)


def parse_chip(text: str) -> dict:
    match = re.search(r"(?:Chip is|Chip type:)\s*(ESP32[^\r\n]*)", text, re.I)
    chip = match.group(1).strip() if match else None
    size = re.search(r"(?:Detected flash size|Flash size):\s*(\d+)\s*(MB|KB)", text, re.I)
    chip_upper = chip.upper() if chip else ""
    if chip_upper.startswith("ESP32-S3"):
        family, route = "esp32s3", "usb_hid"
    elif chip_upper.startswith("ESP32-S2"):
        family, route = "esp32s2", "usb_hid"
    elif re.match(r"ESP32-(?:C3|C6|H2)\b", chip_upper):
        family, route = chip.split()[0].lower().replace("-", ""), "ble_hid"
    elif re.match(r"ESP32(?:\s|$|-D|\(\w)", chip_upper):
        family, route = "esp32", "ble_hid"
    else:
        family, route = None, None
    return {"chip": chip, "family": family, "flash_size": f"{size.group(1)}{size.group(2).upper()}" if size else None,
            "native_usb_hid": family in {"esp32s3", "esp32s2"}, "control_route": route,
            "pcb_model": "not_determined_from_chip_information"}


def candidate_ports(devices: dict) -> list[str]:
    return [p["DeviceID"] for p in devices.get("ports", [])
            if USB_BRIDGES.search(p.get("PNPDeviceID", ""))]


def windows_devices() -> dict:
    script = r"""
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$ports = @(Get-CimInstance Win32_SerialPort | Select-Object DeviceID,Name,PNPDeviceID)
$usb = @(Get-CimInstance Win32_PnPEntity | Where-Object {
  $_.PNPDeviceID -match 'USB\\VID_(10C4|1A86|303A|0403)'
} | Select-Object Name,PNPDeviceID,ConfigManagerErrorCode)
@{ports=$ports;usb=$usb} | ConvertTo-Json -Depth 4 -Compress
"""
    process = subprocess.run(["powershell.exe", "-NoProfile", "-Command", script],
                             capture_output=True, text=True, encoding="utf-8", timeout=20)
    if process.returncode:
        raise RuntimeError("Cannot query Windows device information")
    return json.loads(process.stdout)


def probe(port: str, executable: str) -> dict:
    output = []
    for command in ("chip-id", "flash-id"):
        result = subprocess.run([executable, "--port", port, "--no-stub", command], capture_output=True,
                                text=True, encoding="utf-8", errors="replace", timeout=30)
        if result.returncode:
            raise RuntimeError(f"{command} failed on {port}: {(result.stderr or result.stdout)[-800:]}")
        output.append(result.stdout)
    report = parse_chip("\n".join(output))
    if not report["chip"]:
        raise RuntimeError("Chip output could not be identified; inspect esptool version")
    return {"status": "identified", "port": port, **report}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", help="Explicit serial port; required if more than one is present")
    parser.add_argument("--esptool", default=shutil.which("esptool") or shutil.which("esptool.exe"))
    args = parser.parse_args()
    try:
        devices = windows_devices() if sys.platform == "win32" else {"ports": [], "usb": []}
        port = args.port
        if not port:
            ports = candidate_ports(devices)
            if len(ports) == 1:
                port = ports[0]
            elif any(d.get("ConfigManagerErrorCode") == 28 for d in devices.get("usb", [])):
                print(json.dumps({"status": "driver_missing", "devices": devices,
                                  "help": "Install the official signed USB-UART driver, then retry."}))
                return 2
            else:
                print(json.dumps({"status": "select_port", "devices": devices,
                                  "help": "Connect a board and pass --port explicitly."}))
                return 2
        if not args.esptool:
            parser.error("esptool is not installed; install it from PyPI")
        print(json.dumps(probe(port, args.esptool), indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status": "error", "detail": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
