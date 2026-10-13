#pragma once
#include <ArduinoJson.h>

struct BleDiagnostics {
    bool link, authenticated, keyboardSubscribed, mouseSubscribed;
    int authError;  // -1 means no recorded failure.
};

inline void addBleDiagnostics(JsonDocument &doc, const BleDiagnostics &state) {
    auto out = doc["ble_state"].to<JsonObject>();
    out["link"] = state.link;
    out["authenticated"] = state.authenticated;
    out["keyboard_subscribed"] = state.keyboardSubscribed;
    out["mouse_subscribed"] = state.mouseSubscribed;
    if (state.authError < 0) out["auth_error"] = nullptr;
    else out["auth_error"] = state.authError;
}
