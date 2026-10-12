"""Dependency-free identification and supported build layouts, shared with CLI tools."""
from __future__ import annotations

import re

PROFILES = {
    "esp32dev": ("ble_bridge", "esp32", 0, 4, 0x1000, 0x1E0000),
    "esp32_s3_devkitc": ("usb_bridge", "esp32s3", 9, 8, 0, 0x330000),
    "xiao_esp32s3": ("usb_bridge", "esp32s3", 9, 8, 0, 0x330000),
    "esp32_s3_zero": ("usb_bridge", "esp32s3", 9, 4, 0, 0x1E0000),
}


def parse_chip(text: str) -> dict:
    match = re.search(r"(?:Chip is|Chip type:)\s*(ESP32[^\r\n]*)", text, re.I)
    chip = match.group(1).strip() if match else None
    size = re.search(r"(?:Detected flash size|Flash size):\s*(\d+)\s*(MB|KB)", text, re.I)
    mac = re.search(r"\bMAC:\s*([0-9a-f]{2}(?::[0-9a-f]{2}){5})\b", text, re.I)
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
    flash = int(size.group(1)) * (1024 * 1024 if size.group(2).upper() == "MB" else 1024) if size else None
    return {"chip": chip, "family": family,
            "flash_size": f"{size.group(1)}{size.group(2).upper()}" if size else None,
            "flash_bytes": flash, "mac": mac.group(1).lower() if mac else None,
            "native_usb_hid": family in {"esp32s3", "esp32s2"}, "control_route": route,
            "pcb_model": "not_determined_from_chip_information"}
