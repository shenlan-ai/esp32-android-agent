# Using ESP32 Android Agent

[Project overview](../README.en.md) · [中文自动任务说明](AGENT-USAGE.md)

## Start the workbench

Source use requires Python 3.10+ and [Android Platform Tools](https://developer.android.com/tools/releases/platform-tools). Create a virtual environment, install `./server`, and run `python -m android_agent` with that environment's Python. Windows portable use requires the whole extracted folder and Google's complete `platform-tools` folder beside the executable. There is no official binary release yet; contributor builds are described in [PORTABLE.md](PORTABLE.md).

The default URL is `http://127.0.0.1:8890`. The launcher prints its address and data directory. Defaults store settings and traces in the user directory `.esp32-android-agent`; `--data-dir` overrides it. `--adb` accepts an absolute executable path, `--port` changes the HTTP port, and `--diagnose` reports installation information without model keys. The portable launcher opens a browser unless `--no-browser` is set; source use can request `--open-browser`.

Keep the service running while using the workbench. Closing the page leaves background tasks running. Stop an Android task with **Emergency stop** or Esc. Exit the service with Ctrl+C and wait for shutdown; an in-progress firmware write is allowed to finish.

## Connect and try ADB control

1. Enable Developer options and USB debugging on your phone. Connect a data cable, unlock it and allow this computer's debugging prompt.
2. Click **Refresh devices** and select an authorized phone. If it is unauthorized/offline, resolve that on the phone; the app will not send input to it.
3. Check the live screen, choose a harmless screen, and try a tap. The workbench removes letterboxing from pointer coordinates. Drag to swipe, hold to long press, or use the wheel to scroll. Basic text input is printable ASCII.
4. Check the current control mode before every task. ADB mode needs no ESP32. A failed HID connection remains unavailable until explicitly restored; it does not fall back to ADB.

For wireless ADB, enable the phone's **Wireless debugging → Pair device with pairing code**. The pairing address and six-digit code are used for pairing; the separate connection address is used to connect. These ports are different and may change. **Discover services** can find advertised endpoints; manual addresses remain available. Phone/network restarts may require reconnection. The target Android versions are 15/16/17, and OEM behavior still requires physical testing.

## ESP32 hardware

Use only a profile matching the chip and flash capacity. Classic ESP32 is `esp32dev`/4MB BLE. S3 DevKitC-1 N8 and XIAO use their distinct 8MB profiles; S3 Zero uses the 4MB profile. ESP32-S2/C3/C6/H2 have no accepted firmware in this version. A USB serial bridge is not the main chip, and a UART connector cannot provide native USB HID.

### Install firmware

Stop any task and switch to **ADB control** first. Connect the board to the computer and select its port under **ESP32 HID control**. Open **Install or update board firmware**:

1. **Identify board** reads the chip, MAC and flash. It resets the board but does not write flash or load a RAM stub. Use the manufacturer's BOOT/RESET instructions if initial ROM download mode is needed.
2. Choose a matching firmware profile. For S3 8MB, use the model printed on your board; the chip alone cannot distinguish DevKitC from XIAO.
3. **Back up current program** reads the entire flash, verifies the length and SHA256, and stores a complete backup in `firmware-backups` under the data directory. Download and keep it. It may contain private settings or keys from the old program.
4. Check the overwrite confirmation and click **Write and verify**. The one-use confirmation expires after five minutes. The same board identity, backup and staged images are checked again. Failure or expiry requires fresh identification and backup; writes are never automatically replayed.

Keep USB power and the cable connected while writing. Writing and read-back verification cannot be cancelled from the page; page refresh and phone stop do not cancel them. Forced process termination, power loss or a disconnected cable can leave flash incomplete. Preserve the original backup. Recovery is a deliberate overwrite: identify the same device and capacity, verify the full backup's SHA256, then follow [esptool's write-flash instructions](https://docs.espressif.com/projects/esptool/en/latest/esp32/esptool/basic-commands.html#write-binary-data-to-flash-write-flash) to restore the full image at address `0x0`. The wizard does not restore automatically.

Portable packages include the separate GPL firmware tool and image catalog. Source users install `./server[firmware]`, build the four profiles with PlatformIO, run `python scripts/collect_firmware.py --output` with a new directory, and start the workbench with `--firmware-dir` pointing at that directory. PlatformIO is a contributor build dependency; portable users do not need Arduino or Node. Missing firmware tools/assets leave ADB and the normal workbench available.

### Classic ESP32 BLE

Keep the board connected to the computer. On the phone, pair **Android Agent BLE** in Bluetooth settings. Connect the phone through USB or wireless ADB and select it in the workbench. Confirm that this board is paired with that phone, then choose **Use BLE control**. No board Wi-Fi is needed. The connected COM5 classic board has firmware 0.1.0 and passed board communication checks; its phone-side input remains unaccepted. See [BLE setup](BLE-SETUP.md) for the build/protocol details.

### ESP32-S3 native USB

First pair/connect the phone with **wireless ADB**. With S3's native USB port attached to the computer, use **ESP32-S3 native USB setup** to save the 2.4GHz Wi-Fi name/password and the computer's LAN IPv4 address. Do not use `127.0.0.1`; that would refer to the board itself. Provisioning creates a pairing identity and starts the separate board listener, normally TCP 8891. The web page remains on localhost.

Use a trusted LAN and allow the board listener through the computer's private-network firewall. Then move S3's native USB port to the phone's OTG port, enable OTG if your phone requires it, wait for the authenticated board connection, confirm the target phone and choose **Use S3 USB control**. Native USB enumeration cannot prove which phone is connected. Authentication does not encrypt the TCP connection. More details: [USB setup](USB-SETUP.md).

### Calibrate and accept manual input

If available, disable phone pointer acceleration. The horizontal/vertical edge probes return the pointer to the top-left and move a specified count; they do not click. Reduce the count toward the threshold that just reaches the edge, then save calibration for the current phone, board/mode and screenshot dimensions. Check actual center and edge targets. Edge calibration is not proof of accuracy across the entire screen.

Rotation, pointer-speed changes or another phone can invalidate calibration. Recheck before starting tasks. Use [the acceptance checklist](ACCEPTANCE.md); software simulation and firmware read-back cannot prove phone input.

## Configure a vision model

Enter an OpenAI-compatible API base URL including its API prefix, a vision model name and an optional key. The app appends `/chat/completions`. The actor model is used for decisions; an empty planner model reuses the actor configuration for separate planning/verification calls. Local compatible services may need no key. No specific provider is required.

Optional provider parameters accept a JSON object, for example `{"temperature":0.1}`. A supported provider may use `{"max_completion_tokens":2048}` instead of the default `max_tokens:1000`; that override must be 64–4096. The app controls messages, model name and stream settings. **Test model** sends a synthetic green image and no phone input. A valid response proves protocol connectivity, not task judgment quality.

Task screenshots are sent to this configured endpoint. Model images are JPEG, resized proportionally to at most 1280 pixels on the longest side. Coordinates describe the full screenshot in the 0–1000 range. Decide whether that endpoint and the screen content are appropriate before running the task.

## Run, pause and verify

Use a visible, specific [example goal](EXAMPLES.md). The app plans, observes a fresh screen, chooses one action, and independently verifies the visible result. A model's `done` response is checked against a new screen and the full goal. Models can misjudge; check the outcome yourself before relying on it.

While running, manual input/device changes are rejected. Choose **Pause and take over**, wait for **Paused; manual takeover allowed**, then intervene. Resume observes and replans rather than replaying the old action. Stay on the same phone and control route while paused; stop before switching either. Black/protected screens, connection loss and stale calibration pause execution. Reconnect/unlock/recalibrate, check the visible state, then resume.

Esc or **Emergency stop** cancels pending task work and reports input release. An already submitted action may have taken effect even if cancelled or timed out; that result is recorded as uncertain. BLE board-side cleanup is different from confirmed phone-side release. Never repeat unknown input without first observing its effect.

## Limits and records

Set maximum actions, active time and token usage before starting. Manual pause time is excluded from active time. Submitted but unconfirmed actions count toward the action limit. Token usage uses provider-reported `usage` when available; missing, failed or cancelled calls use a labeled estimate. Limits do not provide an exact provider billing cap or fixed price.

Local `tasks/<task-id>` records contain events and summaries. Known configured keys/tokens are redacted, but goals, model text and screen content may still contain personal data. Screenshot saving is off by default; enabling it writes before/after images. Without saving, only recent in-memory images are available and may disappear after completion/clear. The page retains 100 recent steps; export contains the full local event log. **Clear records** clears the current view, not disk history. Review/redact exports before sharing.

Current evidence and remaining checks are in [COMPATIBILITY.md](COMPATIBILITY.md) and [ACCEPTANCE.md](ACCEPTANCE.md). Windows portable smoke and offline demos are not physical-device or real-model acceptance.
