#pragma once
#include "action_engine.h"
#include <ArduinoJson.h>
#include <string.h>

inline bool boundedInteger(JsonObjectConst obj, const char *key, int &target, int lo, int hi) {
    if (!obj[key].is<int>()) return false;
    target = obj[key].as<int>(); return target >= lo && target <= hi;
}
inline bool validProtocolVersion(JsonObjectConst obj) {
    return obj["v"].is<int>() && obj["v"].as<int>() == 1;
}

template<class Text> bool prepareHidAction(JsonObjectConst obj, ScheduledJob<Text> &next) {
    const char *action = obj["action"].as<const char *>();
    if (!action) return false;
    next.kind = action; next.duration = 60;
    if (next.kind.length() != obj["action"].as<JsonString>().size()) return false;
    bool valid = true;
    if (next.kind == "move") {
        valid = boundedInteger(obj, "dx", next.dx, -4000, 4000) && boundedInteger(obj, "dy", next.dy, -4000, 4000);
        next.stage = 1;
    } else if (next.kind == "tap" || next.kind == "long_press" || next.kind == "swipe" || next.kind == "scroll" || next.kind == "locate") {
        valid = boundedInteger(obj, "x", next.dx, 0, 4000) && boundedInteger(obj, "y", next.dy, 0, 4000);
        next.homeLeft = 50;
        if (next.kind == "long_press" || next.kind == "swipe") {
            int duration = 0;
            valid = valid && boundedInteger(obj, "duration_ms", duration, next.kind == "long_press" ? 400 : 50, 5000);
            next.duration = duration;
        }
        if (next.kind == "swipe") {
            int x2 = 0, y2 = 0;
            valid = valid && boundedInteger(obj, "x2", x2, 0, 4000) && boundedInteger(obj, "y2", y2, 0, 4000);
            next.endX = x2 - next.dx; next.endY = y2 - next.dy;
        }
        if (next.kind == "scroll") valid = valid && boundedInteger(obj, "lines", next.endY, -10, 10) && next.endY;
    } else if (next.kind == "type") {
        const char *text = obj["text"].as<const char *>();
        next.text = text ? text : "";
        valid = text && next.text.length() > 0 && next.text.length() <= 512
            && next.text.length() == obj["text"].as<JsonString>().size();
        for (size_t i = 0; i < next.text.length(); ++i) { uint8_t key, mods; if (!asciiHid(next.text[i], key, mods)) valid = false; }
        next.stage = 5;
    } else if (next.kind == "key") {
        const char *name = obj["key"].as<const char *>();
        if (!name || strlen(name) != obj["key"].as<JsonString>().size()) return false;
        const char *names[] = {"enter","backspace","esc","tab","space","right","left","down","up"};
        const uint8_t codes[] = {40,42,41,43,44,79,80,81,82};
        valid = false;
        for (size_t i = 0; i < 9; ++i) if (name && strcmp(name, names[i]) == 0) { next.key = codes[i]; valid = true; }
        next.stage = 7;
    } else if (next.kind == "wait") {
        int duration = 0; valid = boundedInteger(obj, "duration_ms", duration, 50, 5000);
        next.nextAt += duration; next.stage = 4;
    } else valid = false;
    if (!valid) return false;
    for (JsonPairConst entry : obj) {
        const char *key = entry.key().c_str();
        if (!strcmp(key, "v") || !strcmp(key, "session") || !strcmp(key, "id") || !strcmp(key, "op") || !strcmp(key, "action")) continue;
        bool allowed = false;
        if (!strcmp(key, "x") || !strcmp(key, "y")) allowed = next.kind == "tap" || next.kind == "long_press" || next.kind == "swipe" || next.kind == "scroll" || next.kind == "locate";
        else if (!strcmp(key, "x2") || !strcmp(key, "y2")) allowed = next.kind == "swipe";
        else if (!strcmp(key, "dx") || !strcmp(key, "dy")) allowed = next.kind == "move";
        else if (!strcmp(key, "duration_ms")) allowed = next.kind == "long_press" || next.kind == "swipe" || next.kind == "wait";
        else if (!strcmp(key, "lines")) allowed = next.kind == "scroll";
        else if (!strcmp(key, "text")) allowed = next.kind == "type";
        else if (!strcmp(key, "key")) allowed = next.kind == "key";
        if (!allowed) return false;
    }
    return true;
}
