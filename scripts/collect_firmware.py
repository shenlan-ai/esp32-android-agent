"""Validate and collect compiled firmware; never access serial ports or flash a board."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))
from android_agent.board_info import PROFILES as PROFILES  # noqa: E402
from android_agent.firmware_catalog import sha256 as sha256  # noqa: E402
from android_agent.firmware_catalog import validate_profile as validate_profile  # noqa: E402


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
