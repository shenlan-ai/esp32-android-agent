#include "action_engine.h"
#include "protocol_validation.h"
#include <cassert>
#include <iostream>
#include <string>
#include <utility>
#include <vector>

using Job = ScheduledJob<std::string>;
struct Sink {
    Job &job;
    explicit Sink(Job &value) : job(value) {}
    int moves = 0, sumX = 0, sumY = 0, presses = 0, finishes = 0;
    std::vector<int> keys;
    bool held = false;
    uint32_t now = 0, finishedAt = 0;
    std::vector<uint32_t> motionTimes;
    std::vector<std::pair<int, int>> reports;
    std::vector<bool> heldReports;
    void mouse(int x, int y, int) {
        ++moves; sumX += x; sumY += y; motionTimes.push_back(now); reports.emplace_back(x, y);
        heldReports.push_back(held);
    }
    void key(uint8_t key, uint8_t) { keys.push_back(key); }
    void press() { ++presses; held = true; }
    void finish() { ++finishes; finishedAt = now; job.active = false; held = false; key(0, 0); }
};

void checkTrajectory(const std::vector<std::pair<int, int>> &reports, size_t begin, int x, int y) {
    int length = std::max(hidAbs(x), hidAbs(y));
    int steps = (length + HID_STEP - 1) / HID_STEP;
    assert(reports.size() >= begin + steps);
    int reachedX = 0, reachedY = 0;
    for (int i = 1; i <= steps; ++i) {
        auto delta = reports[begin + i - 1];
        assert(hidAbs(delta.first) <= HID_STEP && hidAbs(delta.second) <= HID_STEP);
        assert(delta.first || delta.second);
        assert(x < 0 ? delta.first <= 0 : delta.first >= 0);
        assert(y < 0 ? delta.second <= 0 : delta.second >= 0);
        reachedX += delta.first; reachedY += delta.second;
        // Each report stays within half a count of the uniform segment position.
        assert(2 * hidAbs(reachedX * steps - x * i) <= steps);
        assert(2 * hidAbs(reachedY * steps - y * i) <= steps);
    }
    assert(reachedX == x && reachedY == y);
}

int main() {
    // Actual report trajectories, not merely the final totals, must be straight.
    for (const auto &target : std::vector<std::pair<int, int>>{
            {4000,1},{1,4000},{800,80},{80,800},{18,10},{1,1},{7,2},{4000,4000},{0,4000},{4000,0},{0,0}}) {
        for (int signX : {-1,1}) for (int signY : {-1,1}) for (int stage : {1,3}) {
            Job line; line.active = true; line.kind = stage == 1 ? "move" : "swipe"; line.stage = stage;
            line.dx = target.first * signX; line.dy = target.second * signY;
            line.motionInterval = line.interval = 50;
            Sink lineSink{line};
            for (uint32_t now = 0; now < 30000; ++now) {
                lineSink.now = now; advanceHid(line, now, lineSink);
            }
            assert(lineSink.finishes == 1);
            int steps = (std::max(target.first, target.second) + HID_STEP - 1) / HID_STEP;
            assert(lineSink.moves == steps);
            checkTrajectory(lineSink.reports, 0, target.first * signX, target.second * signY);
            for (size_t i = 1; i < lineSink.motionTimes.size(); ++i)
                assert(lineSink.motionTimes[i] - lineSink.motionTimes[i-1] == 50);
        }
    }

    // A different slope after press starts a fresh segment, including short/negative axes.
    Job segments; segments.active = true; segments.kind = "swipe";
    segments.dx = 80; segments.dy = 240; segments.endX = -80; segments.endY = 7;
    segments.duration = 1000;
    Sink segmentsSink{segments};
    for (uint32_t now = 0; now < 2000; ++now) advanceHid(segments, now, segmentsSink);
    assert(segmentsSink.finishes == 1 && segmentsSink.presses == 1 && !segmentsSink.held);
    assert(segmentsSink.moves == 40 && segmentsSink.sumX == 0 && segmentsSink.sumY == 247);
    checkTrajectory(segmentsSink.reports, 0, 80, 240);
    checkTrajectory(segmentsSink.reports, 30, -80, 7);

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
    // BLE homing settles without sending or pressing, then uses one calibrated pace.
    Job slow; slow.active = true; slow.kind = "locate"; slow.homeLeft = 2;
    slow.dx = 18; slow.dy = 10; slow.motionInterval = 50; slow.homeSettleMs = 600;
    Sink slowSink{slow};
    for (uint32_t now = 0; now < 900; ++now) {
        slowSink.now = now; advanceHid(slow, now, slowSink);
        if (now >= 20 && now < 620) assert(slowSink.moves == 2 && slowSink.presses == 0);
    }
    assert((slowSink.motionTimes == std::vector<uint32_t>{0,10,620,670,720}));
    assert(slowSink.finishes == 1 && slowSink.presses == 0);

    // Pressed movement never resets the BLE pacing to the USB default.
    Job slowDrag; slowDrag.active = true; slowDrag.kind = "swipe";
    slowDrag.motionInterval = 50; slowDrag.dx = 16; slowDrag.endX = 24; slowDrag.duration = 50;
    Sink slowDragSink{slowDrag};
    for (uint32_t now = 0; now < 500; ++now) {
        slowDragSink.now = now; advanceHid(slowDrag, now, slowDragSink);
    }
    assert((slowDragSink.motionTimes == std::vector<uint32_t>{0,50,150,200,250}));
    assert(slowDragSink.presses == 1 && slowDragSink.finishedAt == 300 && !slowDragSink.held);

    // Stop during the quiet settle interval prevents the delayed positive reports.
    Job quiet; quiet.active = true; quiet.kind = "tap"; quiet.homeLeft = 1;
    quiet.dx = 16; quiet.motionInterval = 50; quiet.homeSettleMs = 600;
    Sink quietSink{quiet}; advanceHid(quiet, 0, quietSink); advanceHid(quiet, 10, quietSink);
    quietSink.finish();
    for (uint32_t now = 11; now < 2000; ++now) advanceHid(quiet, now, quietSink);
    assert(quietSink.moves == 1 && quietSink.presses == 0);

    // Settle deadlines work when millis() wraps between homing and positioning.
    Job quietWrap; quietWrap.active = true; quietWrap.kind = "locate"; quietWrap.homeLeft = 1;
    quietWrap.nextAt = 0xffffffc0; quietWrap.dx = 8;
    quietWrap.motionInterval = 50; quietWrap.homeSettleMs = 600;
    Sink quietWrapSink{quietWrap};
    advanceHid(quietWrap, 0xffffffc0, quietWrapSink); advanceHid(quietWrap, 0xffffffca, quietWrapSink);
    uint32_t due = quietWrap.nextAt;
    advanceHid(quietWrap, due-1, quietWrapSink); assert(quietWrapSink.moves == 1);
    advanceHid(quietWrap, due, quietWrapSink); assert(quietWrapSink.moves == 2);
    advanceHid(quietWrap, due+50, quietWrapSink); assert(quietWrapSink.finishes == 1);

    // The maximum two-stage BLE displacement completes inside the host's 60s bound.
    Job maximum; maximum.active = true; maximum.kind = "swipe"; maximum.homeLeft = 50;
    maximum.motionInterval = 50; maximum.homeSettleMs = 600;
    maximum.dx = 4000; maximum.dy = 4000; maximum.endX = -4000; maximum.endY = -4000;
    maximum.duration = 5000;
    Sink maxSink{maximum};
    for (uint32_t now = 0; now < 60000; ++now) {
        maxSink.now = now; advanceHid(maximum, now, maxSink);
    }
    assert(maxSink.finishes == 1 && maxSink.finishedAt < 60000 && !maxSink.held);
    assert(maxSink.moves == 1050 && maxSink.sumX == -127*50 && maxSink.sumY == -127*50);
    // One path, including a repeated point and closed return, stays pressed.
    for (uint32_t interval : {10u, 50u}) {
        assert(!deserializeJson(document, R"({"action":"path","points":[[16,24],[56,32],[56,32],[24,80],[16,24]],"duration_ms":1000})"));
        Job path; assert(prepareHidAction(document.as<JsonObjectConst>(), path));
        path.homeLeft = 0; path.motionInterval = interval; path.active = true;
        Sink pathSink{path};
        for (uint32_t now = 0; now < 5000; ++now) { pathSink.now = now; advanceHid(path, now, pathSink); }
        assert(pathSink.presses == 1 && pathSink.finishes == 1 && !pathSink.held);
        assert(pathSink.sumX == 16 && pathSink.sumY == 24);
        checkTrajectory(pathSink.reports, 0, 16, 24);
        size_t offset = 3;
        for (size_t i = 1; i < path.pointCount; ++i) {
            int x = path.points[i].x - path.points[i-1].x, y = path.points[i].y - path.points[i-1].y;
            checkTrajectory(pathSink.reports, offset, x, y);
            offset += (std::max(hidAbs(x), hidAbs(y)) + 7) / 8;
        }
        assert(pathSink.reports.size() == offset);
        for (size_t i = 0; i < offset; ++i) assert(pathSink.heldReports[i] == (i >= 3));
        for (size_t i = 4; i < offset; ++i) assert(pathSink.motionTimes[i] - pathSink.motionTimes[i-1] == interval);
        assert(pathSink.finishedAt - path.pressedAt >= 1000);
    }
    // Structure, strict scalar types, coordinate bounds, extra fields, and total budget.
    for (const char *bad : {
        R"({"action":"path","points":[[0,0]],"duration_ms":50})",
        R"({"action":"path","points":[[0,0],[1,true]],"duration_ms":50})",
        R"({"action":"path","points":[[0,0],[1,2.1]],"duration_ms":50})",
        R"({"action":"path","points":[[0,0],[1,"2"]],"duration_ms":50})",
        R"({"action":"path","points":[[0,0],[1,2,3]],"duration_ms":50})",
        R"({"action":"path","points":[[0,0],{"x":1,"y":2}],"duration_ms":50})",
        R"({"action":"path","points":[[0,0],[4001,2]],"duration_ms":50})",
        R"({"action":"path","points":[[0,0],[-1,2]],"duration_ms":50})",
        R"({"action":"path","points":[[0,0],[1,2]],"duration_ms":true})",
        R"({"action":"path","points":[[0,0],[1,2]],"duration_ms":5001})",
        R"({"action":"path","points":[[0,0],[1,2]],"duration_ms":50,"x":0})",
        R"({"action":"path","points":[[0,0],[4000,0],[4000,1]],"duration_ms":50})",
    }) { assert(!deserializeJson(document, bad)); Job invalid; assert(!prepareHidAction(document.as<JsonObjectConst>(), invalid)); }
    document.clear(); document["action"] = "path"; document["duration_ms"] = 50;
    auto tooMany = document["points"].to<JsonArray>();
    for (size_t i = 0; i < 21; ++i) { auto point = tooMany.add<JsonArray>(); point.add(0); point.add(0); }
    Job overPoints; assert(!prepareHidAction(document.as<JsonObjectConst>(), overPoints));
    // Maximum first positioning plus 500 pressed reports finishes before host timeout.
    assert(!deserializeJson(document, R"({"action":"path","points":[[4000,4000],[0,0]],"duration_ms":5000})"));
    Job maxPath; assert(prepareHidAction(document.as<JsonObjectConst>(), maxPath));
    maxPath.active = true; maxPath.motionInterval = 50; maxPath.homeSettleMs = 600;
    Sink maxPathSink{maxPath};
    for (uint32_t now = 0; now < 60000; ++now) { maxPathSink.now = now; advanceHid(maxPath, now, maxPathSink); }
    assert(maxPathSink.finishes == 1 && maxPathSink.presses == 1 && maxPathSink.finishedAt < 60000);
    assert(maxPathSink.moves == 1050 && !maxPathSink.held);
    // Cancelling a pressed later segment makes subsequent calls emit nothing.
    assert(!deserializeJson(document, R"({"action":"path","points":[[0,0],[16,0],[16,100],[0,0]],"duration_ms":5000})"));
    Job cancelledPath; assert(prepareHidAction(document.as<JsonObjectConst>(), cancelledPath));
    cancelledPath.active = true; cancelledPath.homeLeft = 0; cancelledPath.motionInterval = 50;
    Sink cancelPathSink{cancelledPath};
    for (uint32_t now = 0; now < 220; ++now) advanceHid(cancelledPath, now, cancelPathSink);
    assert(cancelledPath.pointIndex == 3 && cancelPathSink.held);
    int sent = cancelPathSink.moves; cancelPathSink.finish();
    for (uint32_t now = 220; now < 20000; ++now) advanceHid(cancelledPath, now, cancelPathSink);
    assert(cancelPathSink.moves == sent && !cancelPathSink.held);
    // All duplicate points hold until deadline, including millis() wrap.
    assert(!deserializeJson(document, R"({"action":"path","points":[[0,0],[0,0],[0,0]],"duration_ms":500})"));
    Job zeroPath; assert(prepareHidAction(document.as<JsonObjectConst>(), zeroPath));
    zeroPath.active = true; zeroPath.homeLeft = 0; zeroPath.nextAt = 0xfffffff0;
    Sink zeroPathSink{zeroPath};
    advanceHid(zeroPath, 0xfffffff0, zeroPathSink);
    assert(zeroPathSink.held && zeroPathSink.moves == 0);
    advanceHid(zeroPath, 0xfffffffa, zeroPathSink);
    advanceHid(zeroPath, 483, zeroPathSink); assert(zeroPathSink.held);
    advanceHid(zeroPath, 484, zeroPathSink); assert(!zeroPathSink.held && zeroPathSink.finishes == 1);
    std::cout << "continuous path scenarios passed\n";
    std::cout << "firmware scheduler and protocol: 27 scenarios passed\n";
    std::cout << "88 vector trajectories and segment reset passed\n";
}
