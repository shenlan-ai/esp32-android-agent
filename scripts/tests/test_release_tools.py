import importlib.util
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))


def module(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


firmware = module("collect_firmware")
release = module("build_portable")
smoke = module("smoke_portable")


def fake_images(folder, profile):
    _, _, chip, _, _, size = firmware.PROFILES[profile]
    folder.mkdir(parents=True, exist_ok=True)
    header = bytearray(24)
    header[0] = 0xE9
    header[12:14] = chip.to_bytes(2, "little")
    for name in ("firmware.bin", "bootloader.bin"):
        (folder / name).write_bytes(header)
    app = bytearray(32)
    app[:4] = b"\xaa\x50\x00\x10"
    app[4:8] = (0x10000).to_bytes(4, "little")
    app[8:12] = size.to_bytes(4, "little")
    (folder / "partitions.bin").write_bytes(app)
    boot_app = folder.parent / "boot_app0.bin"
    boot_app.write_bytes(bytes(0x2000))
    return boot_app


class ReleaseTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("git"), "Release source verification requires git")
    def test_upstream_export_is_pinned_clean_and_excludes_sdk(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cache = root / "cache"
            checkout = cache / "library"
            (checkout / "cores").mkdir(parents=True)
            (checkout / "sdk").mkdir()
            (checkout / "cores/example.cpp").write_text("// LGPL source\n")
            (checkout / "LICENSE.txt").write_text("License terms\n")
            (checkout / "sdk/unneeded.bin").write_bytes(b"unneeded SDK")
            for args in (("init", "-q"), ("config", "user.name", "Release test"),
                         ("config", "user.email", "release-test@example.invalid"), ("add", "."),
                         ("commit", "-qm", "test fixture")):
                subprocess.run(["git", *args], cwd=checkout, check=True, capture_output=True)
            commit = release.command("git", "rev-parse", "HEAD", cwd=checkout)
            (root / "packaging").mkdir()
            lock = {"sources": [{"name": "library", "version": "1", "commit": commit,
                                  "paths": ["cores", "LICENSE.txt"]}]}
            (root / "packaging/sources.json").write_text(json.dumps(lock))
            target = root / "sources"
            target.mkdir()
            with patch.object(release, "ROOT", root):
                records = release.collect_upstream(cache, target)
                archive = target / records[0]["archive"]
                with tarfile.open(archive) as source:
                    self.assertEqual(set(source.getnames()), {"cores/example.cpp", "LICENSE.txt"})
                self.assertEqual(firmware.sha256(archive), records[0]["sha256"])
                (checkout / "cores/example.cpp").write_text("modified source\n")
                with self.assertRaises(subprocess.CalledProcessError):
                    release.collect_upstream(cache, target)

    def test_bundled_unowned_third_party_file_cannot_omit_its_license(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "site-packages").mkdir()
            unknown = root / "site-packages/unknown.py"
            unknown.write_text("# No distribution metadata\n")
            toc = root / "Analysis.toc"
            toc.write_text(repr([("unknown", str(unknown.resolve()), "PYMODULE")]))
            with self.assertRaisesRegex(ValueError, "no distribution owner"):
                release.bundled_distributions(toc)

    def test_all_profile_layouts_and_checksums(self):
        with tempfile.TemporaryDirectory() as temp:
            for name, config in firmware.PROFILES.items():
                folder = Path(temp) / name
                report = firmware.validate_profile(folder, fake_images(folder, name), name)
                self.assertEqual(report["images"][0]["offset"], config[4])
                self.assertEqual(report["chip_id"], config[2])
                self.assertEqual(report["app_size"], config[5])
                self.assertEqual(len(report["images"][-1]["sha256"]), 64)

    def test_wrong_chip_and_wrong_partition_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "build"
            boot = fake_images(folder, "esp32_s3_zero")
            with self.assertRaisesRegex(ValueError, "Wrong chip"):
                firmware.validate_profile(folder, boot, "esp32dev")
            (folder / "partitions.bin").write_bytes(bytes(32))
            with self.assertRaisesRegex(ValueError, "OTA_0"):
                firmware.validate_profile(folder, boot, "esp32_s3_zero")

    def test_oversized_app_and_partition_overlap_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "build"
            boot = fake_images(folder, "esp32dev")
            with (folder / "firmware.bin").open("ab") as stream:
                stream.truncate(0x1E0001)
            with self.assertRaisesRegex(ValueError, "exceeds"):
                firmware.validate_profile(folder, boot, "esp32dev")
            boot = fake_images(folder, "esp32dev")
            app = (folder / "partitions.bin").read_bytes()
            extra = bytearray(app)
            extra[3] = 0x11
            (folder / "partitions.bin").write_bytes(app + extra)
            with self.assertRaisesRegex(ValueError, "Overlapping partitions"):
                firmware.validate_profile(folder, boot, "esp32dev")

    def test_inventory_detects_changed_and_unlisted_files(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            file = folder / "program.exe"
            file.write_bytes(b"program")
            (folder / "checksums.json").write_text(json.dumps(release.inventory(folder)))
            smoke.verify_inventory(folder)
            file.write_bytes(b"corrupt")
            with self.assertRaisesRegex(ValueError, "Corrupt"):
                smoke.verify_inventory(folder)
            file.write_bytes(b"program")
            (folder / "private.json").write_text("private data")
            with self.assertRaisesRegex(ValueError, "Unexpected extra"):
                smoke.verify_inventory(folder)

    def test_manifest_cannot_escape_package(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "checksums.json").write_text(json.dumps({"../outside": {"size": 1, "sha256": "fake"}}))
            with self.assertRaisesRegex(ValueError, "Unsafe"):
                smoke.verify_inventory(folder)

    def test_project_source_excludes_private_and_reference_data(self):
        for name in (".runtime-local/preferences.json", "esp32-iphone-agent/server.py", "server/.env",
                     "hardware/ble_bridge/.pio/build/esp32dev/firmware.bin", "docs/test.local.json"):
            self.assertFalse(release.source_file_allowed(name), name)
        for name in (".env.example", "server/android_agent/launcher.py", "hardware/usb_bridge/src/main.cpp"):
            self.assertTrue(release.source_file_allowed(name), name)

    def test_copy_rechecks_source_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            framework = root / "framework"
            (framework / "tools/partitions").mkdir(parents=True)
            (framework / "tools/partitions/boot_app0.bin").write_bytes(bytes(0x2000))
            for name, config in firmware.PROFILES.items():
                fake_images(root / "hardware" / config[0] / ".pio/build" / name, name)
            copy = firmware.shutil.copyfile

            def corrupt(source, target):
                copy(source, target)
                target.write_bytes(b"corrupted copy")

            with (patch.object(firmware.shutil, "copyfile", side_effect=corrupt),
                  self.assertRaisesRegex(ValueError, "changed during copy")):
                firmware.collect(root, framework, root / "output")
            self.assertFalse((root / "output/manifest.json").exists())
