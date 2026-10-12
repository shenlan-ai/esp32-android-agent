import importlib.util
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
