import hashlib
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1]))
spec = importlib.util.spec_from_file_location("flash_board", Path(__file__).parents[1] / "flash_board.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class FlashTests(unittest.TestCase):
    def test_complete_backup_uses_conservative_transfer_and_records_actual_digest(self):
        data = b"\xa5" * (4 * 1024 * 1024)
        with tempfile.TemporaryDirectory() as folder:
            def read(command, **kwargs):
                self.assertEqual(command[:9], ["esptool", "--port", "COM5", "--baud",
                                              "115200", "read-flash", "0", "0x400000", command[-1]])
                self.assertEqual(kwargs, {"check": True, "timeout": 600})
                Path(command[-1]).write_bytes(data)
            with patch.object(module.subprocess, "run", side_effect=read) as process, \
                    patch("builtins.print"):
                path = module.backup("esptool", "COM5", Path(folder))
            process.assert_called_once()
            self.assertEqual(path.read_bytes(), data)
            self.assertEqual(path.with_suffix(".sha256").read_text(encoding="utf-8"),
                             f"{hashlib.sha256(data).hexdigest()}  {path.name}\n")

    def test_failed_backup_never_starts_write_or_records_complete_digest(self):
        with tempfile.TemporaryDirectory() as folder:
            def fail(command, **kwargs):
                Path(command[-1]).write_bytes(b"partial")
                raise subprocess.CalledProcessError(1, command)
            with patch.object(sys, "argv", ["flash_board", "--port", "COM5", "--esptool", "esptool",
                                            "--write", "--confirm-overwrite", "--backup-dir", folder]), \
                    patch.object(module, "probe", return_value={"family": "esp32", "flash_size": "4MB"}), \
                    patch.object(module, "images", return_value=["0x10000", "app.bin"]), \
                    patch.object(module.subprocess, "run", side_effect=fail) as process, \
                    patch("builtins.print"):
                self.assertEqual(module.main(), 1)
            process.assert_called_once()
            self.assertEqual(process.call_args.args[0][5], "read-flash")
            self.assertEqual(list(Path(folder).glob("*.sha256")), [])

    def test_write_retains_existing_baud_and_bounded_timeout(self):
        with patch.object(module.subprocess, "run") as process:
            module.run("esptool", "COM5", "write-flash", "0x10000", "app.bin")
        process.assert_called_once_with(["esptool", "--port", "COM5", "--baud", "460800",
                                         "write-flash", "0x10000", "app.bin"], check=True, timeout=180)

    def test_classic_ota_zero_partition_is_valid_and_factory_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            boot_app = root / 'tools/partitions/boot_app0.bin'
            boot_app.parent.mkdir(parents=True)
            boot_app.write_bytes(b'placeholder')
            image = bytearray(24)
            image[0] = 0xE9
            (root / 'bootloader.bin').write_bytes(image)
            (root / 'firmware.bin').write_bytes(image)
            partition = bytearray(32)
            partition[:4] = b'\xaa\x50\x00\x10'
            partition[4:8] = (0x10000).to_bytes(4,'little')
            partition[8:12] = (0x1E0000).to_bytes(4,'little')
            (root / 'partitions.bin').write_bytes(partition)
            self.assertEqual(len(module.images(root, root)), 8)
            partition[3] = 0
            (root / 'partitions.bin').write_bytes(partition)
            with self.assertRaisesRegex(ValueError, 'Partition table'):
                module.images(root, root)

    def test_s3_firmware_artifact_rejected_even_on_classic_board(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            boot_app = root / 'tools/partitions/boot_app0.bin'
            boot_app.parent.mkdir(parents=True)
            boot_app.write_bytes(b'placeholder')
            image = bytearray(24)
            image[0] = 0xE9
            (root / 'bootloader.bin').write_bytes(image)
            (root / 'partitions.bin').write_bytes(b'placeholder')
            image[12] = 9  # ESP32-S3 chip ID.
            (root / 'firmware.bin').write_bytes(image)
            with self.assertRaisesRegex(ValueError, 'not a classic'):
                module.images(root, root)

    def test_rejects_wrong_chip_and_flash(self):
        for report in ({"family": "esp32s3", "flash_size": "4MB"},
                       {"family": "esp32", "flash_size": "8MB"}, {}):
            with self.assertRaises(ValueError):
                module.require_classic(report)

    def test_write_requires_explicit_confirmation_before_any_device_io(self):
        with patch.object(sys, "argv", ["flash_board", "--port", "COM5", "--write"]), \
                patch.object(module, "probe") as probe, \
                patch.object(module, "backup") as backup:
            with self.assertRaises(SystemExit):
                module.main()
            probe.assert_not_called()
            backup.assert_not_called()

    def test_incomplete_backup_prevents_writing(self):
        with tempfile.TemporaryDirectory() as folder:
            def incomplete(*args, **kwargs):
                Path(args[-1]).write_bytes(b"incomplete")
            with patch.object(module, "run", side_effect=incomplete):
                with self.assertRaisesRegex(ValueError, "Incomplete"):
                    module.backup("esptool", "COM5", Path(folder))


if __name__ == "__main__":
    unittest.main()
