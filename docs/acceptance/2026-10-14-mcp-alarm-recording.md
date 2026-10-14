# Codex MCP alarm recording

Date: 2026-10-14 (Asia/Shanghai)

**Current public MP4: 5× speed**, 48.40 seconds, 547,378 bytes, SHA256 `9d8bbabae52c482bad0277cd1f615e4c6e383543900baca9abc4511d0c97f7ca`. The original-speed durations, sizes and hash below describe the source recording history. The current file uniformly accelerates that complete two-part demo without new cuts; playback duration is not real task time. See [current media properties and processing](../videos/README.md). OpenSpec: `speed-up-mcp-demo-videos`.

This Codex desktop session used the local `android_agent` MCP bridge with the selected Redmi Note14 5G (24094RAD4C), Android 15 / API 35, classic ESP32-D0WD-V3 / 4 MB and BLE firmware 0.1.4. The controller reported calibrated HID readiness and the advertised action subset before every input.

The MCP sequence opened the preinstalled Clock app after system installation prompts. The user completed the first-use privacy choice. MCP created a new alarm for **2026-10-15 at 07:30 (phone local time)**, left repeat as **one time**, saved it enabled, and obtained a fresh screenshot showing the new 07:30 row alongside the existing disabled 06:00, 07:00 and 08:00 alarms. It later reopened the new alarm, checked 07:30 and one-time repeat, saved the unchanged values and checked the enabled list again. No pre-existing alarm was edited or deleted. `android_stop` returned `hid_release_sent` with `firmware_in_progress=false` after both checks.

Every phone input followed `android_status -> android_screenshot -> one android_action -> verification screenshot`. ADB was used only to start/stop native `screenrecord`, pull the resulting file and read screenshots; it did not inject Android input. The recording was cropped from 720×1600 to 720×1512, encoded at 30 fps H.264/yuv420p with fast-start metadata and fully decoded after encoding.

The public demo joins two original-speed recordings, 175.47 and 66.43 seconds, with about 24 minutes between them not recorded. The first reached Android's time limit before initial saving; that save and its MCP verification are outside the first clip. The second shows the real reopened settings and final list. The combined file is 241.90 seconds, 1,846,045 bytes, SHA256 `4756c688de36f9d5e23fa8cecd5514ac162e03ce9d70c0c0fde4dfa44eeabc7a`. Native private recordings and action logs remain in ignored `.runtime-local/`.

Earlier attempts are retained as failures: a launcher swipe opened a news feed; stale observation and unsupported BLE navigation were rejected; an explicitly selected ADB-mode home/tap returned generic `device_rejected`, with no diagnosed underlying cause. Those recordings are not published. The successful replay used only advertised BLE actions and new observations. Some exploratory wheel scroll/taps completed without changing the time; visual checks guided subsequent swipes rather than assuming command success meant goal success.

This proves the documented MCP flow on this phone, firmware and controller. It does not prove that the Clock package is present or configured on every Android image, nor does it verify that the alarm eventually rings.
