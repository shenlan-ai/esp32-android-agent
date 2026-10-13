// Serial-to-BLE HID bridge for classic ESP32. See hardware/PROTOCOL.md.
// MIT; ESP32 Android Agent contributors.
// Pointer homing approach adapted from esp32-iphone-agent, Copyright (c) 2026 Henry Yuan.
// https://github.com/onehumanbeing/esp32-iphone-agent (see repository LICENSE / NOTICE).
#include "action_engine.h"
#include "ble_diagnostics.h"
#include <atomic>
#include <Arduino.h>
#include <ArduinoJson.h>
#include "protocol_validation.h"
#include <BLEDevice.h>
#include <BLE2902.h>
#include <BLEHIDDevice.h>
#include <BLESecurity.h>
#include <esp_system.h>

constexpr size_t LINE_LIMIT = 1024;
BLEHIDDevice *hid;
BLECharacteristic *keyboardInput, *mouseInput;
std::atomic<bool> authenticated{false}, restartAdvertising{false};
std::atomic<bool> linkConnected{false};
std::atomic<int> authError{-1};
std::atomic<bool> reportFailed{false};
bool previousConnection = false;
String session, inputLine;
uint32_t heartbeatAt = 0, lastId = 0;
bool droppingLine = false;
uint8_t buttons = 0;

// Report 1: boot-style keyboard. Report 2: relative mouse, wheel and pan.
const uint8_t REPORT_MAP[] = {
    0x05,0x01,0x09,0x06,0xA1,0x01,0x85,0x01,0x05,0x07,
    0x19,0xE0,0x29,0xE7,0x15,0x00,0x25,0x01,0x75,0x01,0x95,0x08,0x81,0x02,
    0x95,0x01,0x75,0x08,0x81,0x01,0x95,0x06,0x75,0x08,0x15,0x00,0x25,0x65,
    0x05,0x07,0x19,0x00,0x29,0x65,0x81,0x00,
    0x05,0x08,0x19,0x01,0x29,0x05,0x95,0x05,0x75,0x01,0x91,0x02,
    0x95,0x01,0x75,0x03,0x91,0x01,0xC0,
    0x05,0x01,0x09,0x02,0xA1,0x01,0x85,0x02,0x09,0x01,0xA1,0x00,
    0x05,0x09,0x19,0x01,0x29,0x05,0x15,0x00,0x25,0x01,0x95,0x05,0x75,0x01,0x81,0x02,
    0x95,0x01,0x75,0x03,0x81,0x01,0x05,0x01,0x09,0x30,0x09,0x31,0x09,0x38,
    0x15,0x81,0x25,0x7F,0x75,0x08,0x95,0x03,0x81,0x06,
    0x05,0x0C,0x0A,0x38,0x02,0x15,0x81,0x25,0x7F,0x75,0x08,0x95,0x01,0x81,0x06,0xC0,0xC0
};

using Job = ScheduledJob<String>;
Job job;
String lastStatus, lastError;

bool subscribed(BLECharacteristic *input) {
    auto descriptor = static_cast<BLE2902 *>(input->getDescriptorByUUID(uint16_t(0x2902)));
    return descriptor && descriptor->getNotifications();
}
bool hidReady() { return authenticated && keyboardInput && mouseInput && subscribed(keyboardInput) && subscribed(mouseInput); }

void addDiagnostics(JsonDocument &doc) {
    addBleDiagnostics(doc, {linkConnected.load(), authenticated.load(),
        keyboardInput && subscribed(keyboardInput), mouseInput && subscribed(mouseInput), authError.load()});
}

void mouseReport(int x = 0, int y = 0, int wheel = 0) {
    uint8_t data[] = {buttons, uint8_t(x), uint8_t(y), uint8_t(wheel), 0};
    mouseInput->setValue(data, sizeof(data));
    if (authenticated && subscribed(mouseInput)) mouseInput->notify();
    else if (job.active) reportFailed = true;
}
void keyReport(uint8_t key = 0, uint8_t modifiers = 0) {
    uint8_t data[] = {modifiers, 0, key, 0, 0, 0, 0, 0};
    keyboardInput->setValue(data, sizeof(data));
    if (authenticated && subscribed(keyboardInput)) keyboardInput->notify();
    else if (job.active) reportFailed = true;
}
void releaseInputs() { buttons = 0; mouseReport(); keyReport(); }

void reply(uint32_t id, const char *status, const char *error = "") {
    JsonDocument doc;
    doc["v"] = 1; doc["session"] = session; doc["id"] = id;
    doc["status"] = status; doc["ble_connected"] = hidReady();
    if (!strcmp(status, "stopped")) doc["release_sent"] = hidReady() && !reportFailed;
    if (id == job.id && (!strcmp(status, "done") || !strcmp(status, "cancelled"))) {
        doc["elapsed_ms"] = job.elapsedMs; doc["button_held_ms"] = job.heldMs;
    }
    if (*error) doc["error"] = error;
    addDiagnostics(doc);
    serializeJson(doc, Serial); Serial.println();
}
void finish(const char *status, const char *error = "") {
    job.elapsedMs = millis() - job.startedAt;
    job.heldMs = job.hasPressed ? millis() - job.pressedAt : 0;
    releaseInputs();
    if (reportFailed && !strcmp(status, "done")) { status = "error"; error = "hid_report_failed"; }
    job.active = false; lastStatus = status; lastError = error;
    reply(job.id, status, error);
}
void invalidate(const char *error) {
    if (job.active) finish("error", error);
    else releaseInputs();
    session = "";
}


void consume(const String &line) {
    JsonDocument doc;
    auto parsed = deserializeJson(doc, line);
    if (parsed || !doc.is<JsonObject>()) { reply(0, "error", "invalid_json"); return; }
    JsonObjectConst obj = doc.as<JsonObjectConst>();
    uint32_t id = obj["id"].is<uint32_t>() ? obj["id"].as<uint32_t>() : 0;
    if (!validProtocolVersion(obj)) { reply(id, "error", "protocol_version"); return; }
    String op = obj["op"].is<const char *>() ? obj["op"].as<String>() : "";
    if (op == "hello") {
        if (!id) { reply(id, "error", "invalid_id"); return; }
        invalidate("new_session");
        char buffer[33]; snprintf(buffer, sizeof(buffer), "%08lx%08lx%08lx%08lx",
            (unsigned long)esp_random(), (unsigned long)esp_random(),
            (unsigned long)esp_random(), (unsigned long)esp_random());
        session = buffer; lastId = 0; lastStatus = ""; heartbeatAt = millis(); reportFailed = false;
        JsonDocument out;
        out["v"] = 1; out["session"] = session; out["id"] = id; out["status"] = "hello";
        out["chip"] = "esp32"; out["firmware"] = "0.1.4";
        out["ble_name"] = "Android Agent BLE"; out["ble_connected"] = hidReady();
        auto caps = out["capabilities"].to<JsonArray>();
        for (const char *cap : {"tap", "swipe", "path", "long_press", "scroll", "type", "key", "wait"}) caps.add(cap);
        addDiagnostics(out);
        serializeJson(out, Serial); Serial.println(); return;
    }
    if (session.isEmpty() || !obj["session"].is<const char *>() || obj["session"].as<String>() != session) {
        reply(id, "error", "stale_session"); return;
    }
    if (op == "heartbeat") { heartbeatAt = millis(); reply(id, "heartbeat"); return; }
    // Stop is always serviced even while a gesture is active.
    if (op == "stop") {
        reportFailed = false;
        if (job.active) finish("cancelled"); else releaseInputs();
        reply(id, "stopped"); return;
    }
    if (op == "status") { reply(id, "ready"); return; }
    if (op != "action" || !id) { reply(id, "error", "invalid_command"); return; }
    switch (classifyCommand(id, lastId, job.active)) {
        case CommandDisposition::Duplicate:
            reply(id, job.active ? "running" : lastStatus.c_str(), lastError.c_str()); return;
        case CommandDisposition::Old: reply(id, "error", "old_command"); return;
        case CommandDisposition::Busy: reply(id, "error", "busy"); return;
        case CommandDisposition::New: break;
    }
    if (!hidReady()) { reply(id, "error", "ble_disconnected"); return; }

    Job next;
    next.id = id; next.nextAt = millis(); next.startedAt = next.nextAt;
    if (!prepareHidAction(obj, next)) { reply(id, "error", "invalid_action"); return; }
    // Pace relative movement below typical BLE connection batching rates.
    // Homing keeps its fast saturation reports, then settles without blocking the loop.
    next.motionInterval = 50;
    next.homeSettleMs = next.homeLeft ? 600 : 0;
    if (next.kind == "move") next.interval = next.motionInterval;
    lastId = id; lastStatus = "running"; lastError = ""; next.active = true; job = next;
    reply(id, "accepted");
}

struct HidSink {
    void mouse(int x, int y, int wheel) { mouseReport(x, y, wheel); }
    void key(uint8_t key, uint8_t mods) { keyReport(key, mods); }
    void press() { buttons = 1; mouseReport(); }
    void finish() { ::finish("done"); }
} sink;

class ServerCallbacks : public BLEServerCallbacks {
    void onConnect(BLEServer *) override { linkConnected = true; }
    void onDisconnect(BLEServer *) override {
        linkConnected = false; authenticated = false; authError = -1; restartAdvertising = true;
    }
};
class SecurityCallbacks : public BLESecurityCallbacks {
    uint32_t onPassKeyRequest() override { return 0; }
    void onPassKeyNotify(uint32_t) override {}
    bool onConfirmPIN(uint32_t) override { return false; }
    bool onSecurityRequest() override { return true; }
    void onAuthenticationComplete(esp_ble_auth_cmpl_t result) override {
        authError = result.success ? -1 : result.fail_reason;
        authenticated = result.success;
    }
};
class ReportCallbacks : public BLECharacteristicCallbacks {
    void onStatus(BLECharacteristic *, Status status, uint32_t) override {
        if (status != SUCCESS_NOTIFY && status != SUCCESS_INDICATE) reportFailed = true;
    }
};

void setup() {
    Serial.begin(115200); inputLine.reserve(LINE_LIMIT);
    BLEDevice::init("Android Agent BLE");
    BLEDevice::setEncryptionLevel(ESP_BLE_SEC_ENCRYPT);
    BLEDevice::setSecurityCallbacks(new SecurityCallbacks());
    auto server = BLEDevice::createServer(); server->setCallbacks(new ServerCallbacks());
    hid = new BLEHIDDevice(server);
    keyboardInput = hid->inputReport(1); mouseInput = hid->inputReport(2); hid->outputReport(1);
    keyboardInput->setCallbacks(new ReportCallbacks()); mouseInput->setCallbacks(new ReportCallbacks());
    keyboardInput->setAccessPermissions(ESP_GATT_PERM_READ_ENCRYPTED);
    mouseInput->setAccessPermissions(ESP_GATT_PERM_READ_ENCRYPTED);
    hid->manufacturer()->setValue("ESP32 Android Agent");
    hid->pnp(0x02, 0x303A, 0x4001, 0x0100); hid->hidInfo(0, 1);
    auto security = new BLESecurity();
    security->setAuthenticationMode(ESP_LE_AUTH_BOND); security->setCapability(ESP_IO_CAP_NONE);
    security->setKeySize(16); security->setInitEncryptionKey(ESP_BLE_ENC_KEY_MASK | ESP_BLE_ID_KEY_MASK);
    security->setRespEncryptionKey(ESP_BLE_ENC_KEY_MASK | ESP_BLE_ID_KEY_MASK);
    hid->reportMap(const_cast<uint8_t *>(REPORT_MAP), sizeof(REPORT_MAP)); hid->startServices();
    auto advertising = server->getAdvertising();
    advertising->setAppearance(0x03C0); advertising->addServiceUUID(hid->hidService()->getUUID());
    advertising->setScanResponse(true); advertising->start(); hid->setBatteryLevel(100);
    releaseInputs();
}
void loop() {
    if (previousConnection && !authenticated) invalidate("ble_disconnected");
    previousConnection = authenticated;
    if (restartAdvertising.exchange(false)) BLEDevice::startAdvertising();
    if (!session.isEmpty() && heartbeatExpired(millis(), heartbeatAt)) invalidate("heartbeat_expired");
    // Bound work per iteration so input floods cannot starve watchdog or stop.
    for (int n = 0; n < 128 && Serial.available(); ++n) {
        char c = Serial.read();
        if (c == '\n') {
            if (inputLine.endsWith("\r")) inputLine.remove(inputLine.length() - 1);
            if (!droppingLine && !inputLine.isEmpty()) consume(inputLine);
            inputLine = ""; droppingLine = false;
        } else {
            if (inputLine.length() >= LINE_LIMIT) { droppingLine = true; inputLine = ""; }
            if (!droppingLine) inputLine += c;
        }
    }
    advanceHid(job, millis(), sink); delay(1);
    if (reportFailed.exchange(false) && !session.isEmpty()) invalidate("hid_report_failed");
}
