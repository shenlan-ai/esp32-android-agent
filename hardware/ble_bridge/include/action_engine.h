#pragma once
#include <stddef.h>
#include <stdint.h>

constexpr uint32_t HID_REPORT_MS = 10;
constexpr int HID_STEP = 8;
constexpr uint32_t HID_WATCHDOG_MS = 1500;

enum class CommandDisposition { Duplicate, Old, Busy, New };
inline CommandDisposition classifyCommand(uint32_t id, uint32_t previous, bool active) {
    if (id == previous) return CommandDisposition::Duplicate;
    if (id < previous) return CommandDisposition::Old;
    return active ? CommandDisposition::Busy : CommandDisposition::New;
}
inline bool heartbeatExpired(uint32_t now, uint32_t received) {
    return uint32_t(now - received) > HID_WATCHDOG_MS;
}

template<class Text> struct ScheduledJob {
    bool active = false;
    uint32_t id = 0, nextAt = 0, interval = HID_REPORT_MS, duration = 0;
    uint32_t startedAt = 0, pressedAt = 0, releaseAt = 0, elapsedMs = 0, heldMs = 0;
    bool hasPressed = false;
    Text kind, text;
    int stage = 0, homeLeft = 0, dx = 0, dy = 0, endX = 0, endY = 0;
    size_t textIndex = 0;
    uint8_t key = 0, modifiers = 0;
};

inline bool asciiHid(char c, uint8_t &key, uint8_t &mods) {
    mods = 0;
    if (c >= 'a' && c <= 'z') { key = c - 'a' + 4; return true; }
    if (c >= 'A' && c <= 'Z') { key = c - 'A' + 4; mods = 2; return true; }
    if (c >= '1' && c <= '9') { key = c - '1' + 30; return true; }
    if (c == '0') { key = 39; return true; }
    const char *plain = " -=[]\\;'`,./";
    const char *shifted = " _+{}|:\"~<>?";
    const uint8_t codes[] = {44,45,46,47,48,49,51,52,53,54,55,56};
    for (size_t i = 0; i < 12; ++i) {
        if (c == plain[i]) { key = codes[i]; return true; }
        if (c == shifted[i]) { key = codes[i]; mods = 2; return true; }
    }
    const char *symbols = "!@#$%^&*()";
    for (size_t i = 0; i < 10; ++i) if (c == symbols[i]) {
        key = i == 9 ? 39 : 30 + i; mods = 2; return true;
    }
    return false;
}
inline int hidAbs(int value) { return value < 0 ? -value : value; }
inline int hidDelta(int value) { return value < -HID_STEP ? -HID_STEP : value > HID_STEP ? HID_STEP : value; }

// One call emits at most one motion/keyboard step. The serial loop owns cancellation.
template<class Text, class Sink> void advanceHid(ScheduledJob<Text> &job, uint32_t now, Sink &sink) {
    if (!job.active || int32_t(now - job.nextAt) < 0) return;
    job.nextAt = now + job.interval;
    if (job.stage == 0) {
        if (job.homeLeft-- > 0) { sink.mouse(-127, -127, 0); return; }
        job.stage = 1;
    }
    if (job.stage == 1 || job.stage == 3) {
        if (job.dx || job.dy) {
            int sx = hidDelta(job.dx), sy = hidDelta(job.dy);
            sink.mouse(sx, sy, 0); job.dx -= sx; job.dy -= sy; return;
        }
        if (job.stage == 3) {
            if (int32_t(now - job.releaseAt) < 0) { job.stage = 4; job.nextAt = job.releaseAt; }
            else sink.finish();
            return;
        }
        if (job.kind == "move" || job.kind == "locate") { sink.finish(); return; }
        job.stage = 2;
    }
    if (job.stage == 2) {
        if (job.kind == "scroll") { sink.mouse(0, 0, job.endY); sink.finish(); return; }
        sink.press();
        job.hasPressed = true; job.pressedAt = now; job.releaseAt = now + job.duration;
        if (job.kind == "swipe") {
            job.dx = job.endX; job.dy = job.endY; job.stage = 3;
            job.interval = HID_REPORT_MS;
            job.nextAt = now + job.interval;
        } else { job.stage = 4; job.nextAt = now + job.duration; }
        return;
    }
    if (job.stage == 4) { sink.finish(); return; }
    if (job.stage == 5) {
        if (job.textIndex >= job.text.length()) { sink.finish(); return; }
        asciiHid(job.text[job.textIndex++], job.key, job.modifiers);
        sink.key(job.key, job.modifiers); job.stage = 6; job.nextAt = now + 20; return;
    }
    if (job.stage == 6) { sink.key(0, 0); job.stage = 5; job.nextAt = now + 20; return; }
    if (job.stage == 7) { sink.key(job.key, 0); job.stage = 4; job.nextAt = now + 30; }
}
