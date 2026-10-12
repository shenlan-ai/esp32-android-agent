# ESP32 Android Agent

[简体中文](README.md) · [English usage guide](docs/USAGE.en.md)

A local Android vision agent: a vision model plans and verifies actions, an ESP32 sends HID input, and ADB provides screenshots. Classic ESP32 boards use computer serial → BLE keyboard/mouse; ESP32-S3 boards use Wi-Fi → native USB keyboard/mouse with wireless ADB. An explicit ADB control mode lets you try the workflow without a board.

Manual control needs no model account. No Android companion app, root, Node.js, Arduino IDE, project cloud service, or fixed model provider is required for normal use.

The project is in development. The workbench, task execution, pause/takeover, image verification, local traces, firmware installation wizard, and Windows portable build have passed software or offline checks. The connected classic ESP32 has passed firmware flashing and 12 board communication checks. **Real Android input and real vision-model tasks have not yet been accepted.** Android 15/16/17 (API 35/36/37) are compatibility targets; this is not evidence that every phone works. See [validation status](docs/COMPATIBILITY.md).

## Try it without an ESP32

Install Python 3.10+ and Google's [Android Platform Tools](https://developer.android.com/tools/releases/platform-tools). In this checkout on Windows:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e "./server"
.venv\Scripts\python -m android_agent
```

On macOS/Linux, use `.venv/bin/python` instead. Open `http://127.0.0.1:8890`, enable USB debugging on your phone, connect it with a data cable, unlock it and authorize this computer. Refresh devices, select your phone, check the screen, and try a harmless manual tap in **ADB control** mode.

If ADB is not on PATH, pass `--adb` with its absolute executable path. `--diagnose` reports the environment, and `--port` changes the workbench port. Screenshots may contain private information; automatic tasks send them to the model endpoint you configure.

For an automatic task, save your vision model's API base URL, model name and optional key in the workbench. Test the model, then use a short [example goal](docs/EXAMPLES.md). A synthetic image is used for the model connection test; real task execution uses phone screenshots.

## ESP32 control

| Firmware profile | Hardware configuration | Phone input / screenshots |
|---|---|---|
| `esp32dev` | Classic ESP32, 4MB flash | BLE HID / USB or wireless ADB |
| `esp32_s3_devkitc` | ESP32-S3 DevKitC-1 N8, 8MB | Native USB HID / wireless ADB |
| `xiao_esp32s3` | XIAO ESP32S3, 8MB | Native USB HID / wireless ADB |
| `esp32_s3_zero` | ESP32-S3 Zero, 4MB | Native USB HID / wireless ADB |

The connected COM5 board is an ESP32-D0WD-V3 revision 3.1 with 4MB flash, using `esp32dev`. A CP2102/CH340 serial bridge does not identify the ESP chip or prove native USB support. Chip information cannot establish the commercial PCB model. S3 profiles have compiled and passed host/protocol simulation; S3 hardware input remains untested.

The **Install or update board firmware** wizard identifies the board, restricts profiles by chip/flash, creates a full original-flash backup, requires explicit overwrite confirmation, then writes and reads back the images. Installation does not run automatically. Classic ESP32 stays attached to the computer and pairs with the phone as **Android Agent BLE**. S3 is configured over native USB first, then moves to the phone's OTG port; its screenshot connection must be wireless ADB. Calibrate the pointer and accept manual input before starting model tasks. [Detailed steps](docs/USAGE.en.md#esp32-hardware).

## Windows portable build

Contributors can build a Windows x64 ZIP containing Python, the workbench, four firmware profiles, a separate firmware tool, licenses and corresponding sources. Extract the whole directory and run `esp32-android-agent.exe`. Obtain Platform Tools from Google and place the complete `platform-tools` folder beside the executable; **ADB is not redistributed in the ZIP**.

There is no official binary release yet. [Build and verification instructions](docs/PORTABLE.md) describe the local artifact and the manual GitHub build workflow. The workflow uploads a short-lived artifact after smoke checks; it does not publish a Release.

## Development and acceptance

- [AGENTS.md](AGENTS.md) is the authoritative development policy; [agent.md](agent.md) links to it. Every change uses OpenSpec, including documentation and tooling.
- [Developer workflow](docs/DEVELOPMENT.md) and [contribution guide](CONTRIBUTING.md).
- [Examples](docs/EXAMPLES.md) and [physical-device acceptance checklist](docs/ACCEPTANCE.md).
- Offline development: install `./server[dev]`, then run `python server/tests/agent_demo.py` and open `http://127.0.0.1:8892`. The page is labeled DEMO and uses fake phone/model IO. Stop the demo before running another fixture on that port.

Manual control supports calibrated relative-pointer gestures and printable ASCII input. Unicode, absolute-touch HID, scrcpy video ingestion, companion apps and multiple phones are future capabilities. Unknown input outcomes are observed before recovery; HID disconnects never silently switch input to ADB.

## Upstream and licenses

Based on [esp32-iphone-agent](https://github.com/onehumanbeing/esp32-iphone-agent), with upstream attribution preserved in [NOTICE](NOTICE). Application code is [MIT](LICENSE). The separate [firmware worker](tools/firmware_worker.py) and esptool are GPL-2.0-or-later; firmware and other dependencies have their own licenses. The portable package includes component notices and sources; its components are not all MIT.
