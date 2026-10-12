import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class FirmwareTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("g++"), "Native g++ not available; CI must provide it")
    def test_actual_scheduler_with_fake_hid(self):
        source = Path(__file__).resolve().parents[2] / "hardware/ble_bridge"
        library = source / ".pio/libdeps/esp32dev/ArduinoJson/src"
        if not library.is_dir():
            self.skipTest("Install the fixed ArduinoJson library with PlatformIO before native tests")
        with tempfile.TemporaryDirectory() as folder:
            executable = Path(folder) / "firmware-test.exe"
            subprocess.run([shutil.which("g++"), "-std=c++11", "-Wall", "-Wextra", "-Werror",
                            "-I", str(source / "include"), "-I", str(library), str(source / "tests/action_engine_test.cpp"),
                            "-o", str(executable)], check=True, timeout=120)
            result = subprocess.run([str(executable)], capture_output=True, text=True, check=True, timeout=10)
            self.assertIn("22 scenarios passed", result.stdout)
