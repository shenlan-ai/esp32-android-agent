import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch
from subprocess import CompletedProcess

spec = importlib.util.spec_from_file_location("identify_board", Path(__file__).parents[1] / "identify_board.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class IdentificationTests(unittest.TestCase):
    def test_classic_chip_requires_bluetooth(self):
        result = module.parse_chip("Chip is ESP32-D0WD-V3 (revision v3.1)\nDetected flash size: 4MB")
        self.assertEqual(result["family"], "esp32")
        self.assertEqual(result["control_route"], "ble_hid")
        self.assertFalse(result["native_usb_hid"])

    def test_s3_has_native_usb(self):
        result = module.parse_chip("Chip type: ESP32-S3 (revision v0.2)\nDetected flash size: 8 MB")
        self.assertEqual(result["control_route"], "usb_hid")
        self.assertEqual(result["flash_size"], "8MB")

    def test_c3_usb_serial_is_not_usb_hid(self):
        self.assertFalse(module.parse_chip("Chip type: ESP32-C3 (revision v0.4)")["native_usb_hid"])

    def test_usb_bridge_does_not_identify_chip(self):
        self.assertIsNone(module.parse_chip("CP2102 USB to UART Bridge Controller")["chip"])

    def test_unknown_chip_does_not_guess_classic_or_ble(self):
        for chip in ("ESP32-P4", "ESP32-C2", "ESP32-S4"):
            result = module.parse_chip(f"Chip type: {chip}")
            self.assertIsNone(result["family"])
            self.assertIsNone(result["control_route"])

    def test_excludes_unrelated_serial_port(self):
        devices = {"ports": [
            {"DeviceID": "COM1", "PNPDeviceID": "ACPI\\PNP0501"},
            {"DeviceID": "COM5", "PNPDeviceID": "USB\\VID_10C4&PID_EA60\\0001"},
        ]}
        self.assertEqual(module.candidate_ports(devices), ["COM5"])

    def test_probe_only_uses_read_commands_without_stub(self):
        with patch.object(module.subprocess, "run", side_effect=[
            CompletedProcess([], 0, "Chip type: ESP32-D0WD-V3", ""),
            CompletedProcess([], 0, "Detected flash size: 4MB", ""),
        ]) as run:
            self.assertEqual(module.probe("COM5", "esptool")["flash_size"], "4MB")
            self.assertEqual([call.args[0] for call in run.call_args_list], [
                ["esptool", "--port", "COM5", "--no-stub", "chip-id"],
                ["esptool", "--port", "COM5", "--no-stub", "flash-id"],
            ])


if __name__ == "__main__":
    unittest.main()
