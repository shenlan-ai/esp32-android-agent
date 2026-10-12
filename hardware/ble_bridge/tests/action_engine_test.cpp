#include "action_engine.h"
#include "protocol_validation.h"
#include <cassert>
#include <iostream>
#include <string>
#include <vector>

using Job = ScheduledJob<std::string>;
struct Sink {
    Job &job;
    explicit Sink(Job &value) : job(value) {}
    int moves = 0, sumX = 0, sumY = 0, presses = 0, finishes = 0;
    std::vector<int> keys;
    bool held = false;
    void mouse(int x, int y, int) { ++moves; sumX += x; sumY += y; }
    void key(uint8_t key, uint8_t) { keys.push_back(key); }
    void press() { ++presses; held = true; }
    void finish() { ++finishes; job.active = false; held = false; key(0, 0); }
};

int main() {
    // Calibration moves can never click.
    Job locate; locate.active = true; locate.kind = "locate"; locate.homeLeft = 50; locate.dx = 18; locate.dy = 10;
    Sink a{locate};
    for (uint32_t now = 0; now < 1000; ++now) advanceHid(locate, now, a);
    assert(a.moves == 53 && a.presses == 0 && a.finishes == 1);
    assert(a.sumX == -127 * 50 + 18 && a.sumY == -127 * 50 + 10);

    // Long press duration starts at press, not at initial homing.
    Job hold; hold.active = true; hold.kind = "long_press"; hold.duration = 700;
    Sink b{hold}; advanceHid(hold, 0, b); assert(b.held);
    advanceHid(hold, 699, b); assert(b.held && b.finishes == 0);
    advanceHid(hold, 700, b); assert(!b.held && b.finishes == 1);

    // Clearing active state prevents any further gesture reports after stop.
    Job drag; drag.active = true; drag.kind = "swipe"; drag.endX = 400; drag.endY = -120; drag.duration = 1000;
    Sink c{drag}; advanceHid(drag, 0, c); assert(c.held && drag.stage == 3);
    advanceHid(drag, 20, c); assert(c.moves == 1);
    c.finish(); int emitted = c.moves;
    for (uint32_t now = 21; now < 2000; ++now) advanceHid(drag, now, c);
    assert(c.moves == emitted && !c.held);

    // Long requested duration holds the endpoint, preserving calibrated movement pace.
    Job timed; timed.active = true; timed.kind = "swipe"; timed.endX = 80; timed.duration = 1000;
    Sink paced{timed};
    for (uint32_t now = 0; now < 999; ++now) advanceHid(timed, now, paced);
    assert(paced.moves == 10 && paced.sumX == 80 && paced.held && timed.interval == HID_REPORT_MS);
    advanceHid(timed, 1000, paced); assert(!paced.held && paced.finishes == 1);

    // Characters always have a release between key presses.
    Job type; type.active = true; type.kind = "type"; type.stage = 5; type.text = "Aa";
    Sink d{type};
    for (uint32_t now = 0; now < 200; ++now) advanceHid(type, now, d);
    assert(d.keys.size() == 5 && d.keys[0] == 4 && d.keys[1] == 0 && d.keys[2] == 4 && d.keys[3] == 0);
    assert(d.finishes == 1);
    for (int ascii = 32; ascii <= 126; ++ascii) { uint8_t key, mods; assert(asciiHid(ascii, key, mods)); }
    uint8_t key, mods; assert(!asciiHid('\n', key, mods));

    // millis() wrap does not cause early key release or a permanently held key.
    Job wrap; wrap.active = true; wrap.kind = "key"; wrap.key = 40; wrap.stage = 7; wrap.nextAt = 0xfffffff0;
    Sink e{wrap}; advanceHid(wrap, 0xfffffff0, e); assert(e.keys.size() == 1);
    advanceHid(wrap, 13, e); assert(e.finishes == 0);
    advanceHid(wrap, 14, e); assert(e.finishes == 1);
    // Running and completed duplicate IDs cannot become a fresh action.
    assert(classifyCommand(8, 8, true) == CommandDisposition::Duplicate);
    assert(classifyCommand(8, 8, false) == CommandDisposition::Duplicate);
    assert(classifyCommand(7, 8, false) == CommandDisposition::Old);
    assert(classifyCommand(9, 8, true) == CommandDisposition::Busy);
    assert(classifyCommand(9, 8, false) == CommandDisposition::New);
    assert(!heartbeatExpired(1500, 0) && heartbeatExpired(1501, 0));
    assert(heartbeatExpired(0x1000, 0xfffffff0));
    JsonDocument document;
    for (const char *bad : {
        "{\"action\":\"tap\",\"x\":true,\"y\":1}",
        "{\"action\":\"tap\",\"x\":4001,\"y\":1}",
        "{\"action\":\"tap\",\"x\":1,\"y\":1,\"text\":\"oops\"}",
        "{\"action\":\"long_press\",\"x\":1,\"y\":1,\"duration_ms\":399}",
        "{\"action\":\"scroll\",\"x\":1,\"y\":1,\"lines\":0}",
        "{\"action\":\"key\",\"key\":\"home\"}",
        "{\"action\":\"type\",\"text\":\"a\\nb\"}",
        "{\"action\":\"type\",\"text\":123}",
        "{\"action\":\"wait\",\"duration_ms\":5001}",
        "{\"action\":\"type\",\"text\":\"a\\u0000b\"}",
    }) { assert(!deserializeJson(document, bad)); Job invalid; assert(!prepareHidAction(document.as<JsonObjectConst>(), invalid)); }
    assert(!deserializeJson(document, "{\"action\":\"type\",\"text\":\"a\\\"b\\\\c\"}"));
    Job escaped; assert(prepareHidAction(document.as<JsonObjectConst>(), escaped)); assert(escaped.text == "a\"b\\c");
    assert(!deserializeJson(document, "{\"v\":true}")); assert(!validProtocolVersion(document.as<JsonObjectConst>()));
    assert(!deserializeJson(document, "{\"v\":2}")); assert(!validProtocolVersion(document.as<JsonObjectConst>()));
    std::cout << "firmware scheduler and protocol: 22 scenarios passed\n";
}
