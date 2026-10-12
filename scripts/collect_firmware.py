"""Validate and collect compiled firmware; never access serial ports or flash a board."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

PROFILES = {
    "esp32dev": ("ble_bridge", "esp32", 0, 4, 0x1000, 0x1E0000),
    "esp32_s3_devkitc": ("usb_bridge", "esp32s3", 9, 8, 0, 0x330000),
    "xiao_esp32s3": ("usb_bridge", "esp32s3", 9, 8, 0, 0x330000),
    "esp32_s3_zero": ("usb_bridge", "esp32s3", 9, 4, 0, 0x1E0000),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_profile(build: Path, boot_app: Path, name: str) -> dict:
    _, family, chip, flash_mb, boot_offset, app_size = PROFILES[name]
    entries = [("bootloader.bin", boot_offset, build / "bootloader.bin"),
               ("partitions.bin", 0x8000, build / "partitions.bin"),
               ("boot_app0.bin", 0xE000, boot_app),
               ("firmware.bin", 0x10000, build / "firmware.bin")]
    images = []
    end = 0
    for filename, offset, path in entries:
        if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f"Missing or indirect firmware artifact: {path}")
        size = path.stat().st_size
        if offset < end or offset + size > flash_mb * 1024 * 1024:
            raise ValueError(f"Overlapping or out-of-flash image: {path}")
        end = offset + size
        if filename in {"bootloader.bin", "firmware.bin"}:
            with path.open("rb") as stream:
                header = stream.read(24)
            if (len(header) != 24 or header[0] != 0xE9
                    or int.from_bytes(header[12:14], "little") != chip):
                raise ValueError(f"Wrong chip image for {name}: {path}")
        images.append({"file": filename, "offset": offset, "size": size, "sha256": sha256(path)})
    table = (build / "partitions.bin").read_bytes()
    app = [table[i:i+32] for i in range(0, len(table) - 31, 32)
           if table[i:i+4] == b"\xaa\x50\x00\x10"]
    if (len(app) != 1 or int.from_bytes(app[0][4:8], "little") != 0x10000
            or int.from_bytes(app[0][8:12], "little") != app_size):
        raise ValueError(f"Unexpected OTA_0 partition for {name}")
    if images[-1]["size"] > app_size:
        raise ValueError(f"Application exceeds the partition for {name}")
    # Every concrete partition must fit in the configured flash and be disjoint.
    partitions = []
    for i in range(0, len(table) - 31, 32):
        row = table[i:i+32]
        if row[:2] != b"\xaa\x50":
            break
        offset, size = int.from_bytes(row[4:8], "little"), int.from_bytes(row[8:12], "little")
        if size == 0 or offset < 0x9000 or offset + size > flash_mb * 1024 * 1024:
            raise ValueError(f"Invalid partition range for {name}")
        if any(offset < old_end and old_start < offset + size for old_start, old_end in partitions):
            raise ValueError(f"Overlapping partitions for {name}")
        partitions.append((offset, offset + size))
    return {"profile": name, "family": family, "chip_id": chip,
            "flash_bytes": flash_mb * 1024 * 1024, "flash_mode": "dio", "flash_freq": "40m",
            "app_offset": 0x10000, "app_size": app_size, "images": images}


def collect(root: Path, framework: Path, destination: Path) -> dict:
    boot_app = framework / "tools/partitions/boot_app0.bin"
    profiles = [validate_profile(root / "hardware" / config[0] / ".pio/build" / name,
                                 boot_app, name) for name, config in PROFILES.items()]
    destination.mkdir(parents=True, exist_ok=False)
    for profile in profiles:
        name = profile["profile"]
        build = root / "hardware" / PROFILES[name][0] / ".pio/build" / name
        folder = destination / name
        folder.mkdir()
        for image in profile["images"]:
            source = boot_app if image["file"] == "boot_app0.bin" else build / image["file"]
            target = folder / image["file"]
            shutil.copyfile(source, target)
            if sha256(target) != image["sha256"]:
                raise ValueError(f"Artifact changed during copy: {source}")
    manifest = {"schema": 1, "profiles": profiles}
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--framework", type=Path,
                        default=Path.home() / ".platformio/packages/framework-arduinoespressif32")
    parser.add_argument("--output", type=Path, required=True, help="New output directory")
    args = parser.parse_args()
    collect(args.root, args.framework, args.output)


if __name__ == "__main__":
    main()
