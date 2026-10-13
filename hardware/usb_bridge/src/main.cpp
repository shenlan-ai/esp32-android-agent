// USB HID + CDC bridge, MIT; ESP32 Android Agent contributors.
// Homing approach adapted from esp32-iphone-agent, Copyright (c) 2026 Henry Yuan.
// https://github.com/onehumanbeing/esp32-iphone-agent (see repository LICENSE / NOTICE).
#include <Arduino.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include <WiFi.h>
#include <USB.h>
#include <USBHID.h>
#include <tusb.h>
#include <esp_system.h>
#include <mbedtls/md.h>
#include <lwip/sockets.h>
#include "action_engine.h"
#include "protocol_validation.h"

constexpr size_t LINE_LIMIT = 1024;
constexpr uint32_t AUTH_TIMEOUT_MS = 4000;
const uint8_t descriptor[] = {
    TUD_HID_REPORT_DESC_KEYBOARD(HID_REPORT_ID(1)),
    TUD_HID_REPORT_DESC_MOUSE(HID_REPORT_ID(2))
};
class AgentHid : public USBHIDDevice {
public:
    USBHID sender;
    AgentHid() { USBHID::addDevice(this, sizeof(descriptor)); }
    uint16_t _onGetDescriptor(uint8_t *buffer) override {
        memcpy(buffer, descriptor, sizeof(descriptor)); return sizeof(descriptor);
    }
} hid;
Preferences nvs;
WiFiClient client;
String boardId, session, tcpLine, cdcLine, storedConfig;
String wifiSsid, wifiPass, host, token;
uint16_t servicePort = 0;
bool configured = false, authenticated = false, tcpDropping = false, cdcDropping = false;
bool reportFailed = false, previousUsb = false, refreshNetwork = false;
bool releasePending = false;
uint32_t heartbeatAt = 0, lastId = 0, retryAt = 0, connectedAt = 0;
uint8_t buttons = 0;
using Job = ScheduledJob<String>;
Job job;
String lastStatus, lastError;

bool usbReady() { return tud_mounted() && !tud_suspended(); }
bool sendReport(uint8_t id, const void *data, size_t length) {
    bool ok = usbReady() && hid.sender.SendReport(id, data, length, 20);
    if (!ok) reportFailed = true;
    return ok;
}
void mouseReport(int x = 0, int y = 0, int wheel = 0) {
    uint8_t data[] = {buttons, uint8_t(x), uint8_t(y), uint8_t(wheel), 0};
    sendReport(2, data, sizeof(data));
}
void keyReport(uint8_t key = 0, uint8_t mods = 0) {
    uint8_t data[] = {mods, 0, key, 0, 0, 0, 0, 0};
    sendReport(1, data, sizeof(data));
}
bool releaseInputs() {
    buttons = 0;
    uint8_t mouse[] = {0,0,0,0,0}, keyboard[] = {0,0,0,0,0,0,0,0};
    bool m = sendReport(2, mouse, sizeof(mouse));
    bool k = sendReport(1, keyboard, sizeof(keyboard));
    releasePending = !(m && k);
    return !releasePending;
}
bool emit(JsonDocument &doc) {
    String line; serializeJson(doc, line); line += '\n';
    if (line.length() > LINE_LIMIT || !client.connected()) return false;
    // Arduino WiFiClient::write can wait several seconds on a blocked peer.
    // A single nonblocking send either submits the complete bounded line or closes the session.
    return send(client.fd(), line.c_str(), line.length(), MSG_DONTWAIT) == int(line.length());
}
void reply(uint32_t id, const char *status, const char *error = "", bool released = false) {
    JsonDocument doc;
    doc["v"] = 1; doc["session"] = session; doc["id"] = id;
    doc["status"] = status; doc["usb_connected"] = usbReady();
    if (!strcmp(status, "stopped")) doc["release_sent"] = released;
    if (id == job.id && (!strcmp(status, "done") || !strcmp(status, "cancelled"))) {
        doc["elapsed_ms"] = job.elapsedMs; doc["button_held_ms"] = job.heldMs;
    }
    if (*error) doc["error"] = error;
    if (!emit(doc)) client.stop();
}
void finish(const char *status, const char *error = "") {
    job.elapsedMs = millis() - job.startedAt;
    job.heldMs = job.hasPressed ? millis() - job.pressedAt : 0;
    releaseInputs();
    if (reportFailed && !strcmp(status, "done")) { status = "error"; error = "hid_report_failed"; }
    job.active = false; lastStatus = status; lastError = error;
    reply(job.id, status, error);
}
void disconnect(const char *error) {
    if (job.active) finish("error", error); else releaseInputs();
    job.active = false; session = ""; authenticated = false;
    client.stop(); tcpLine = ""; tcpDropping = false; reportFailed = false;
}
bool hexString(const String &value, size_t length) {
    if (value.length() != length) return false;
    for (size_t i = 0; i < length; ++i) if (!strchr("0123456789abcdef", value[i])) return false;
    return true;
}
bool cleanText(const String &value, size_t limit) {
    if (value.length() > limit) return false;
    for (size_t i = 0; i < value.length(); ++i) if (uint8_t(value[i]) < 32) return false;
    return true;
}
bool configValid(JsonObjectConst obj) {
    for (const char *name : {"ssid", "password", "host", "token"}) {
        if (!obj[name].is<const char *>()) return false;
        String value = obj[name].as<String>();
        if (value.length() != obj[name].as<JsonString>().size()) return false;
    }
    String ssid = obj["ssid"].as<String>(), pass = obj["password"].as<String>();
    String address = obj["host"].as<String>(), key = obj["token"].as<String>();
    IPAddress ip;
    int port = 0;
    return !ssid.isEmpty() && cleanText(ssid, 32) && cleanText(pass, 63)
        && (pass.isEmpty() || pass.length() >= 8) && hexString(key, 64)
        && address.length() <= 15 && ip.fromString(address) && ip[0] && ip[0] != 127 && ip[0] < 224
        && boundedInteger(obj, "port", port, 1, 65535);
}
void loadConfig() {
    JsonDocument doc;
    configured = !deserializeJson(doc, storedConfig) && doc.is<JsonObject>() && configValid(doc.as<JsonObjectConst>());
    if (configured) {
        wifiSsid = doc["ssid"].as<String>(); wifiPass = doc["password"].as<String>();
        host = doc["host"].as<String>(); token = doc["token"].as<String>(); servicePort = doc["port"];
    }
}
void cdcReply(uint32_t id, const char *status) {
    JsonDocument out;
    out["v"] = 1; out["id"] = id; out["status"] = status;
    out["chip"] = "esp32s3"; out["board_id"] = boardId;
    out["protocol"] = "android-agent-usb-v1"; out["firmware"] = "0.1.2";
    out["profile"] = AGENT_BOARD_PROFILE; out["configured"] = configured;
    serializeJson(out, Serial); Serial.println();
}
void consumeCdc(const String &line) {
    JsonDocument doc;
    if (deserializeJson(doc, line) || !doc.is<JsonObject>()) { cdcReply(0, "error"); return; }
    JsonObjectConst obj = doc.as<JsonObjectConst>();
    uint32_t id = obj["id"].is<uint32_t>() ? obj["id"].as<uint32_t>() : 0;
    if (!id || !validProtocolVersion(obj)) { cdcReply(id, "error"); return; }
    String op = obj["op"].is<const char *>() ? obj["op"].as<String>() : "";
    if (op == "get_config") { cdcReply(id, "config"); return; }
    if (op != "configure" || !configValid(obj)) { cdcReply(id, "error"); return; }
    JsonDocument settings;
    for (const char *name : {"ssid", "password", "host", "port", "token"}) settings[name] = obj[name];
    String next; serializeJson(settings, next);
    disconnect("configuration_changed");
    if (nvs.putString("config", next) != next.length()) { cdcReply(id, "error"); return; }
    storedConfig = next; loadConfig(); refreshNetwork = true;
    cdcReply(id, "configured");
}
void consumeTcp(const String &line) {
    JsonDocument doc;
    if (deserializeJson(doc, line) || !doc.is<JsonObject>()) { disconnect("invalid_json"); return; }
    JsonObjectConst obj = doc.as<JsonObjectConst>();
    uint32_t id = obj["id"].is<uint32_t>() ? obj["id"].as<uint32_t>() : 0;
    if (!validProtocolVersion(obj)) { disconnect("protocol_version"); return; }
    String op = obj["op"].is<const char *>() ? obj["op"].as<String>() : "";
    if (!authenticated) {
        String nonce = obj["nonce"].is<const char *>() ? obj["nonce"].as<String>() : "";
        if (op != "challenge" || !hexString(nonce, 64)) { disconnect("authentication_failed"); return; }
        String message = "android-agent-usb-v1:" + nonce + ":" + boardId;
        uint8_t digest[32]; char proof[65];
        int result = mbedtls_md_hmac(mbedtls_md_info_from_type(MBEDTLS_MD_SHA256),
            reinterpret_cast<const uint8_t *>(token.c_str()), token.length(),
            reinterpret_cast<const uint8_t *>(message.c_str()), message.length(), digest);
        if (result) { disconnect("authentication_failed"); return; }
        for (int i = 0; i < 32; ++i) snprintf(proof + i * 2, 3, "%02x", digest[i]);
        JsonDocument out; out["v"] = 1; out["op"] = "authenticate";
        out["board_id"] = boardId; out["proof"] = proof;
        if (!emit(out)) { disconnect("write_failed"); return; }
        authenticated = true; return;
    }
    if (op == "hello") {
        if (!id) { reply(id, "error", "invalid_id"); return; }
        if (job.active) finish("cancelled"); else releaseInputs();
        char buffer[33]; snprintf(buffer, sizeof(buffer), "%08lx%08lx%08lx%08lx",
            (unsigned long)esp_random(), (unsigned long)esp_random(),
            (unsigned long)esp_random(), (unsigned long)esp_random());
        session = buffer; lastId = 0; lastStatus = ""; reportFailed = false; heartbeatAt = millis();
        JsonDocument out;
        out["v"] = 1; out["session"] = session; out["id"] = id; out["status"] = "hello";
        out["chip"] = "esp32s3"; out["firmware"] = "0.1.2"; out["board_id"] = boardId;
        out["profile"] = AGENT_BOARD_PROFILE; out["usb_connected"] = usbReady();
        auto caps = out["capabilities"].to<JsonArray>();
        for (const char *cap : {"tap", "swipe", "path", "long_press", "scroll", "type", "key", "wait"}) caps.add(cap);
        if (!emit(out)) disconnect("write_failed");
        return;
    }
    if (session.isEmpty() || !obj["session"].is<const char *>() || obj["session"].as<String>() != session) {
        reply(id, "error", "stale_session"); return;
    }
    if (op == "heartbeat") { heartbeatAt = millis(); reply(id, "heartbeat"); return; }
    if (op == "stop") {
        reportFailed = false;
        if (job.active) finish("cancelled");
        bool released = releaseInputs(); reply(id, "stopped", "", released); reportFailed = false; return;
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
    if (!usbReady()) { reply(id, "error", "usb_disconnected"); return; }
    if (releasePending) { reply(id, "error", "hid_report_failed"); return; }
    Job next; next.id = id; next.nextAt = millis(); next.startedAt = next.nextAt;
    if (!prepareHidAction(obj, next)) { reply(id, "error", "invalid_action"); return; }
    lastId = id; lastStatus = "running"; lastError = "";
    next.active = true; job = next; reply(id, "accepted");
}
struct HidSink {
    void mouse(int x, int y, int wheel) { mouseReport(x, y, wheel); }
    void key(uint8_t key, uint8_t mods) { keyReport(key, mods); }
    void press() { buttons = 1; mouseReport(); }
    void finish() { ::finish("done"); }
} sink;
template<class Stream> void readLines(Stream &stream, String &line, bool &dropping, void (*consume)(const String &)) {
    for (int n = 0; n < 128 && stream.available(); ++n) {
        char c = stream.read();
        if (c == '\n') {
            if (line.endsWith("\r")) line.remove(line.length() - 1);
            if (!dropping && !line.isEmpty()) consume(line);
            line = ""; dropping = false;
        } else {
            if (line.length() >= LINE_LIMIT) { dropping = true; line = ""; }
            if (!dropping) line += c;
        }
    }
}
void setup() {
    Serial.begin(115200); Serial.setTxTimeoutMs(20);
    cdcLine.reserve(LINE_LIMIT); tcpLine.reserve(LINE_LIMIT);
    hid.sender.begin(); USB.productName("Android Agent USB"); USB.begin();
    WiFi.mode(WIFI_STA); WiFi.setSleep(false); WiFi.setAutoReconnect(true);
    boardId = WiFi.macAddress(); boardId.replace(":", ""); boardId.toLowerCase();
    nvs.begin("agentusb", false); storedConfig = nvs.getString("config", ""); loadConfig();
    if (configured) WiFi.begin(wifiSsid.c_str(), wifiPass.c_str());
}
void loop() {
    uint32_t now = millis();
    bool mounted = usbReady();
    if (previousUsb && !mounted) disconnect("usb_disconnected");
    if (!previousUsb && mounted) { releaseInputs(); reportFailed = false; }
    if (releasePending && mounted && !job.active) { releaseInputs(); reportFailed = false; }
    previousUsb = mounted;
    if (!session.isEmpty() && heartbeatExpired(now, heartbeatAt)) disconnect("heartbeat_expired");
    if (authenticated && session.isEmpty() && now - connectedAt > AUTH_TIMEOUT_MS) disconnect("hello_timeout");
    readLines(Serial, cdcLine, cdcDropping, consumeCdc);
    if (refreshNetwork) {
        WiFi.disconnect(); WiFi.begin(wifiSsid.c_str(), wifiPass.c_str()); refreshNetwork = false; retryAt = now;
    }
    if (client.connected() && WiFi.status() == WL_CONNECTED) {
        if (!authenticated && now - connectedAt > AUTH_TIMEOUT_MS) disconnect("authentication_timeout");
        else readLines(client, tcpLine, tcpDropping, consumeTcp);
    } else {
        if (authenticated || !session.isEmpty() || job.active) disconnect("network_disconnected");
        if (configured && WiFi.status() == WL_CONNECTED && int32_t(now - retryAt) >= 0) {
            // Only retry without an active gesture. connect has a bounded 250ms timeout.
            retryAt = now + 2000; IPAddress ip; ip.fromString(host);
            if (client.connect(ip, servicePort, 250)) {
                client.setNoDelay(true); client.setTimeout(50); connectedAt = millis();
            }
        }
    }
    if (!session.isEmpty() && authenticated) advanceHid(job, millis(), sink);
    if (reportFailed && !session.isEmpty()) disconnect("hid_report_failed");
    reportFailed = false;
    delay(1);
}
