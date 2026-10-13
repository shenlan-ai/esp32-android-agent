#include "ble_diagnostics.h"
#include <cassert>
#include <iostream>
#include <string>

int main() {
    const BleDiagnostics states[] = {
        {false, false, false, false, -1}, {true, false, false, false, -1},
        {true, false, false, false, 5}, {true, true, false, true, -1},
        {true, true, true, false, -1}, {true, true, true, true, -1},
        {true, false, false, false, 255}
    };
    for (const auto &state : states) {
        JsonDocument doc;
        doc["v"] = 1; doc["session"] = std::string(32, 'a'); doc["id"] = 0xffffffffu;
        doc["status"] = "hello"; doc["chip"] = "esp32"; doc["firmware"] = "0.1.2";
        doc["ble_name"] = "Android Agent BLE"; doc["ble_connected"] = false;
        auto caps = doc["capabilities"].to<JsonArray>();
        for (const char *cap : {"tap", "swipe", "long_press", "scroll", "type", "key", "wait"}) caps.add(cap);
        // Include the largest bounded timing fields, even though hello omits them.
        doc["elapsed_ms"] = 0xffffffffu; doc["button_held_ms"] = 0xffffffffu;
        doc["error"] = "heartbeat_expired"; doc["release_sent"] = false;
        addBleDiagnostics(doc, state);
        std::string wire;
        serializeJson(doc, wire);
        assert(wire.size() + 1 < 1024);
        JsonDocument parsed;
        assert(!deserializeJson(parsed, wire));
        auto out = parsed["ble_state"].as<JsonObjectConst>();
        assert(out.size() == 5);
        assert(out["link"].is<bool>() && out["link"].as<bool>() == state.link);
        assert(out["authenticated"].is<bool>() && out["authenticated"].as<bool>() == state.authenticated);
        assert(out["keyboard_subscribed"].is<bool>() && out["keyboard_subscribed"].as<bool>() == state.keyboardSubscribed);
        assert(out["mouse_subscribed"].is<bool>() && out["mouse_subscribed"].as<bool>() == state.mouseSubscribed);
        if (state.authError < 0) assert(out["auth_error"].isNull());
        else assert(out["auth_error"].is<int>() && out["auth_error"].as<int>() == state.authError);
        assert(wire.find("\"mac\":") == std::string::npos && wire.find("\"key\":") == std::string::npos);
        assert(wire.find("secret") == std::string::npos);
    }
    std::cout << "7 diagnostics scenarios passed\n";
}
