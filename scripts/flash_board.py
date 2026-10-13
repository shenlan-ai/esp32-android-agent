"""Back up classic ESP32 flash, or explicitly write the built BLE firmware."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from identify_board import probe

ROOT = Path(__file__).resolve().parents[1]


def run(executable: str, port: str, *args: str, timeout: int = 180, baud: int = 460800) -> None:
    subprocess.run([executable, "--port", port, "--baud", str(baud), *args], check=True, timeout=timeout)


def require_classic(report: dict) -> None:
    if report.get("family") != "esp32" or report.get("flash_size") != "4MB":
        raise ValueError("This firmware requires a classic ESP32 with 4MB flash; no flash was written")


def backup(executable: str, port: str, folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"esp32-{datetime.now():%Y%m%d-%H%M%S}.bin"
    if path.exists():
        raise ValueError("Backup file already exists; retry after one second")
    run(executable, port, "read-flash", "0", "0x400000", str(path), timeout=600, baud=115200)
    if path.stat().st_size != 4 * 1024 * 1024:
        raise ValueError("Incomplete flash backup; firmware write cancelled")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    path.with_suffix(".sha256").write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    print(json.dumps({"backup": str(path), "sha256": digest}))
    return path


def images(build_dir: Path, framework_dir: Path) -> list[str]:
    parts = [
        ("0x1000", build_dir / "bootloader.bin"),
        ("0x8000", build_dir / "partitions.bin"),
        ("0xe000", framework_dir / "tools/partitions/boot_app0.bin"),
        ("0x10000", build_dir / "firmware.bin"),
    ]
    for _, path in parts:
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f"Build artifact missing: {path}")
    for _, path in (parts[0], parts[-1]):
        header = path.read_bytes()[:24]
        if len(header) != 24 or header[0] != 0xE9 or int.from_bytes(header[12:14], "little") != 0:
            raise ValueError(f"Artifact is not a classic ESP32 image: {path}")
    table = parts[1][1].read_bytes()
    application = next((table[i:i+32] for i in range(0, len(table)-31, 32)
                        if table[i:i+2] == b"\xaa\x50" and table[i+2:i+4] == b"\x00\x10"), None)
    if (application is None or int.from_bytes(application[4:8], "little") != 0x10000
            or int.from_bytes(application[8:12], "little") != 0x1E0000):
        raise ValueError("Partition table does not match the classic ESP32 4MB min_spiffs profile")
    if parts[-1][1].stat().st_size > 0x1E0000:
        raise ValueError("Firmware exceeds configured min_spiffs app partition")
    return [value for offset, path in parts for value in (offset, str(path))]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True)
    parser.add_argument("--esptool", default=shutil.which("esptool.exe") or shutil.which("esptool"))
    parser.add_argument("--write", action="store_true", help="Write after making a complete backup")
    parser.add_argument("--confirm-overwrite", action="store_true", help="Confirm replacing existing firmware")
    parser.add_argument("--backup-dir", type=Path, default=ROOT / ".runtime-local/firmware-backups")
    parser.add_argument("--build-dir", type=Path, default=ROOT / "hardware/ble_bridge/.pio/build/esp32dev")
    parser.add_argument("--framework-dir", type=Path,
                        default=Path.home() / ".platformio/packages/framework-arduinoespressif32")
    args = parser.parse_args()
    if args.write and not args.confirm_overwrite:
        parser.error("Writing replaces existing firmware; pass --confirm-overwrite after reviewing it")
    if not args.esptool:
        parser.error("Install esptool before using this tool")
    try:
        require_classic(probe(args.port, args.esptool))
        artifacts = images(args.build_dir, args.framework_dir) if args.write else []
        backup(args.esptool, args.port, args.backup_dir)
        if args.write:
            run(args.esptool, args.port, "write-flash", "--flash-mode", "dio", "--flash-freq", "40m",
                "--flash-size", "4MB", *artifacts)
            print("Firmware written and verified by esptool. Pair the phone and test BLE before claiming compatibility.")
        return 0
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"Firmware operation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
