"""Exercise the real isolated worker with a bound fake ROM connection, no device IO."""
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

SPEC = importlib.util.spec_from_file_location("firmware_worker", Path(__file__).resolve().parents[2] / "tools/firmware_worker.py")
worker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(worker)


def make_catalog(folder, name="esp32dev"):
    from android_agent.firmware_catalog import validate_profile
    config = worker.PROFILES[name]
    target = folder / name
    target.mkdir(parents=True)
    header = bytearray(24)
    header[0] = 0xE9
    header[12:14] = config[2].to_bytes(2, "little")
    for image in ("bootloader.bin", "firmware.bin"):
        (target / image).write_bytes(header)
    app = bytearray(32)
    app[:4] = b"\xaa\x50\x00\x10"
    app[4:8] = (0x10000).to_bytes(4, "little")
    app[8:12] = config[5].to_bytes(4, "little")
    (target / "partitions.bin").write_bytes(app)
    (target / "boot_app0.bin").write_bytes(bytes(0x2000))
    profile = validate_profile(target, target / "boot_app0.bin", name)
    (folder / "manifest.json").write_text(json.dumps({"schema": 1, "profiles": [profile]}))
    return folder


class FakeApi:
    __version__ = "5.3.0"

    def __init__(self, family="esp32", flash_bytes=4194304):
        self.family, self.flash_bytes = family, flash_bytes
        self.mac = (0x10, 0x20, 0x30, 0x40, 0x50, 0x60)
        self.memory = bytearray(b"\xa5" * flash_bytes)
        self.connected = False
        self.attached = False
        self.attach_calls = 0
        self.fail_attach = False
        self.fail_stub = False
        self.loader = SimpleNamespace(DEFAULT_TIMEOUT=3)
        self.connections = 0
        self.stub_calls = 0
        self.write_calls = 0
        self.verify_calls = 0
        self.reset_calls = 0
        self.fail_write = False
        self.fail_verify = False
        self.short_backup = False
        self.disconnect = False
        self.cmds = self

    def detect_chip(self, *, port, baud, connect_attempts):
        self.connections += 1
        self.connected = True
        self.attached = False
        self.rom = SimpleNamespace()
        # A ROM owns this physical memory and identity until it closes.
        parent = self

        class Rom:
            CHIP_NAME = "ESP32" if parent.family == "esp32" else "ESP32-S3"

            def __init__(self):
                self._port = SimpleNamespace(timeout=None)

            def __enter__(self):
                return self

            def __exit__(self, *args):
                parent.connected = False

            def read_mac(self):
                return parent.mac

            def get_chip_description(self):
                return "ESP32-D0WD-V3" if parent.family == "esp32" else "ESP32-S3"

            def run_stub(self):
                assert self._port.timeout == parent.loader.DEFAULT_TIMEOUT
                parent.stub_calls += 1
                if parent.fail_stub:
                    raise TimeoutError("No stub handshake response")
                return self

            def change_baud(self, value):
                assert value == 460800

            def hard_reset(self):
                parent.reset_calls += 1

        self.rom = Rom()
        return self.rom

    def attach_flash(self, rom):
        assert self.connected and rom is self.rom
        self.attach_calls += 1
        if self.fail_attach:
            raise OSError("ROM SPI initialization failed")
        self.attached = True

    def detect_flash_size(self, rom):
        assert self.connected and rom is self.rom and self.attached
        return f"{self.flash_bytes // 1048576}MB"

    def read_flash(self, rom, start, length, *, no_progress):
        assert self.connected and rom is self.rom and no_progress
        return bytes(self.memory[start:start+length - int(self.short_backup)])

    def write_flash(self, rom, images, *, flash_mode, flash_freq, flash_size):
        assert self.connected and rom is self.rom
        assert (flash_mode, flash_freq, flash_size) == ("dio", "40m", f"{self.flash_bytes // 1048576}MB")
        self.write_calls += 1
        if self.fail_write or self.disconnect:
            raise OSError("Disconnected in write; never reconnect")
        for offset, payload in images:
            assert isinstance(payload, bytes)
            self.memory[offset:offset+len(payload)] = payload

    def verify_flash(self, rom, images, *, flash_mode, flash_freq, flash_size):
        assert self.connected and rom is self.rom
        assert (flash_mode, flash_freq, flash_size) == ("dio", "40m", f"{self.flash_bytes // 1048576}MB")
        self.verify_calls += 1
        if self.fail_verify:
            raise ValueError("Read-back failed")
        for offset, payload in images:
            assert bytes(self.memory[offset:offset+len(payload)]) == payload


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.api = FakeApi()
        self.catalog = make_catalog(self.root / "catalog")
        self.backup = self.root / "backup.bin"
        self.backup.write_bytes(self.api.memory)
        self.identity = ["--port", "DEMO-COM", "--family", "esp32", "--mac", "10:20:30:40:50:60", "--flash-bytes", "4194304"]
        self.write_args = ["write", *self.identity, "--backup", str(self.backup), "--backup-sha256", worker.sha256(self.backup),
                           "--catalog", str(self.catalog), "--profile", "esp32dev", "--manifest-sha256", worker.sha256(self.catalog / "manifest.json"), "--confirm-overwrite"]

    def perform(self, args):
        return worker.perform(worker.parser().parse_args(args), self.api)

    def test_diagnose_and_identify_never_load_stub_or_write(self):
        self.assertFalse(self.perform(["diagnose"])["device_used"])
        report = self.perform(["identify", "--port", "DEMO-COM"])
        self.assertEqual(report["identity"]["mac"], "10:20:30:40:50:60")
        self.assertEqual(report["identity"]["flash_bytes"], 4194304)
        self.assertEqual((self.api.connections, self.api.stub_calls, self.api.write_calls), (1, 0, 0))
        self.assertFalse(self.api.connected)
        self.assertEqual(self.api.attach_calls, 1)

    def test_flash_initialization_failure_does_not_load_stub_or_write(self):
        self.api.fail_attach = True
        for args in (["identify", "--port", "DEMO-COM"],
                     ["backup", *self.identity, "--output", str(self.root / "failed.part")],
                     self.write_args):
            with self.assertRaisesRegex(OSError, "initialization"):
                self.perform(args)
            self.assertFalse(self.api.connected)
        self.assertEqual((self.api.connections, self.api.attach_calls), (3, 3))
        self.assertEqual((self.api.stub_calls, self.api.write_calls), (0, 0))
        self.assertFalse((self.root / "failed.part").exists())

    def test_full_backup_uses_one_connection_and_hashes_actual_bytes(self):
        path = self.root / "new.part"
        result = self.perform(["backup", *self.identity, "--output", str(path)])
        self.assertEqual(path.read_bytes(), bytes(self.api.memory))
        self.assertEqual(result["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual((self.api.connections, self.api.stub_calls, self.api.write_calls), (1, 1, 0))

    def test_stub_timeout_closes_without_backup_write_or_reconnection(self):
        self.api.fail_stub = True
        path = self.root / "stub-failed.part"
        for args in (["backup", *self.identity, "--output", str(path)], self.write_args):
            with self.assertRaisesRegex(TimeoutError, "handshake"):
                self.perform(args)
            self.assertFalse(self.api.connected)
        self.assertEqual((self.api.connections, self.api.stub_calls), (2, 2))
        self.assertEqual((self.api.write_calls, self.api.verify_calls), (0, 0))
        self.assertFalse(path.exists())

    def test_wrong_mac_rejected_before_stub_and_flash_write(self):
        self.api.mac = (1, 2, 3, 4, 5, 6)
        with self.assertRaisesRegex(ValueError, "identity changed"):
            self.perform(self.write_args)
        self.assertEqual((self.api.stub_calls, self.api.write_calls), (0, 0))

    def test_unconfirmed_or_bad_backup_does_not_connect(self):
        with self.assertRaisesRegex(ValueError, "confirmation"):
            self.perform(self.write_args[:-1])
        self.backup.write_bytes(b"partial")
        with self.assertRaisesRegex(ValueError, "backup"):
            self.perform(self.write_args)
        self.assertEqual(self.api.connections, 0)

    def test_manifest_or_payload_mutation_refused_before_connect(self):
        (self.catalog / "esp32dev/firmware.bin").write_bytes(b"changed")
        with self.assertRaises(ValueError):
            self.perform(self.write_args)
        self.assertEqual(self.api.connections, 0)

    def test_short_backup_has_no_completed_output(self):
        self.api.short_backup = True
        path = self.root / "partial.part"
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            self.perform(["backup", *self.identity, "--output", str(path)])
        self.assertFalse(path.exists())

    def test_write_and_verify_use_same_rom_and_payloads(self):
        report = self.perform(self.write_args)
        self.assertTrue(report["image_verified"])
        self.assertFalse(report["phone_input_verified"])
        self.assertEqual((self.api.connections, self.api.stub_calls, self.api.write_calls, self.api.verify_calls), (1, 1, 1, 1))
        self.assertFalse(self.api.connected)

    def test_disconnect_or_verification_failure_never_replays(self):
        for flag in ("disconnect", "fail_verify"):
            with self.subTest(flag=flag):
                self.api = FakeApi()
                setattr(self.api, flag, True)
                with self.assertRaises((OSError, ValueError)):
                    self.perform(self.write_args)
                self.assertEqual((self.api.connections, self.api.write_calls), (1, 1))
                self.assertFalse(self.api.connected)
