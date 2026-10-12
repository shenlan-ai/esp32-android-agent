"""Strict, dependency-free firmware catalog and image layout validation."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from .board_info import PROFILES


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


def unique_object(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate firmware manifest key")
        result[key] = value
    return result


class FirmwareCatalog:
    def __init__(self, root: Path | None):
        self.root = root.resolve() if root is not None else None

    def load(self) -> dict:
        if self.root is None:
            raise ValueError("Firmware assets missing; use the portable package or configure --firmware-dir")
        path = self.root / "manifest.json"
        if path.is_symlink():
            raise ValueError("Indirect firmware manifest")
        with path.open("rb") as stream:
            content = stream.read(65537)
        if len(content) > 65536:
            raise ValueError("Firmware manifest is too large")
        data = json.loads(content, object_pairs_hook=unique_object)
        if (not isinstance(data, dict) or set(data) != {"schema", "profiles"}
                or type(data["schema"]) is not int or data["schema"] != 1
                or not isinstance(data["profiles"], list) or not 1 <= len(data["profiles"]) <= 4):
            raise ValueError("Unsupported firmware manifest")
        names = []
        for profile in data["profiles"]:
            if not isinstance(profile, dict) or not isinstance(profile.get("profile"), str):
                raise ValueError("Invalid firmware profile")
            name = profile["profile"]
            if name not in PROFILES or name in names:
                raise ValueError("Unsupported or duplicate firmware profile")
            names.append(name)
        return data

    def describe(self) -> dict:
        try:
            data = self.load()
            return {"available": True, "error": "", "profiles": [
                {"profile": item["profile"], "family": PROFILES[item["profile"]][1],
                 "flash_bytes": PROFILES[item["profile"]][3] * 1024 * 1024}
                for item in data["profiles"]]}
        except (OSError, ValueError):
            return {"available": False, "error": "Firmware assets unavailable; use the portable package or rebuild the catalog", "profiles": []}

    def validate(self, name: str) -> dict:
        data = self.load()
        profile = next((item for item in data["profiles"] if item["profile"] == name), None)
        if profile is None:
            raise ValueError("Choose an available supported firmware profile")
        folder = self.root / name
        if folder.is_symlink() or not folder.resolve().is_relative_to(self.root):
            raise ValueError("Indirect firmware profile directory")
        actual = validate_profile(folder, folder / "boot_app0.bin", name)
        # JSON equality preserves integer/bool distinctions that Python == loses.
        if json.dumps(actual, sort_keys=True) != json.dumps(profile, sort_keys=True):
            raise ValueError("Firmware files do not match their manifest; rebuild the catalog")
        return actual

    def snapshot(self, name: str, destination: Path) -> str:
        profile = self.validate(name)
        destination.mkdir(parents=True, mode=0o700, exist_ok=False)
        folder = destination / name
        folder.mkdir(mode=0o700)
        for image in profile["images"]:
            target = folder / image["file"]
            shutil.copyfile(self.root / name / image["file"], target)
            target.chmod(0o600)
            if sha256(target) != image["sha256"]:
                raise ValueError("Firmware changed while taking its snapshot")
        manifest = destination / "manifest.json"
        manifest.write_text(json.dumps({"schema": 1, "profiles": [profile]}, indent=2) + "\n", encoding="utf-8")
        manifest.chmod(0o600)
        return sha256(manifest)

    def image_bytes(self, name: str, expected_manifest: str) -> tuple[dict, list[tuple[int, bytes]]]:
        if self.root is None or sha256(self.root / "manifest.json") != expected_manifest:
            raise ValueError("The prepared firmware manifest changed")
        profile = self.validate(name)
        images = []
        for image in profile["images"]:
            path = self.root / name / image["file"]
            payload = path.read_bytes()
            if len(payload) != image["size"] or hashlib.sha256(payload).hexdigest() != image["sha256"]:
                raise ValueError("Firmware changed while loading its snapshot")
            images.append((image["offset"], payload))
        return profile, images
