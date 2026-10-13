import base64
import json

import httpx
import pytest

from android_agent.config import ModelSettings
from android_agent.llm import (
    ModelClient,
    ModelCompletionError,
    ModelError,
    ModelProtocolError,
    estimate_tokens,
    parse_decision,
    parse_object,
)


@pytest.mark.parametrize("text", [
    '{"action":"tap","action":"done"}', '{"x":NaN}', '[{}]',
    'Here is JSON: {"action":"done"}', '{} trailing', '```json\n{}\n``` trailing',
])
def test_strict_json_rejects_ambiguous_outputs(text):
    with pytest.raises(ModelProtocolError):
        parse_object(text)


def test_fenced_json_and_capability_arguments():
    assert parse_object('```json\n{"ok":true}\n```') == {"ok": True}
    good = {"action": "tap", "x": 500, "y": 500, "reason": "Open settings", "expected": "Settings visible"}
    assert parse_decision(json.dumps(good), ["tap"], set()).action == "tap"
    for bad in ({**good, "x": True}, {**good, "expected": ""}, {**good, "x": 1001},
                {**good, "frame_id": 2}, {**good, "unexpected": "x"}):
        with pytest.raises(ModelProtocolError):
            parse_decision(json.dumps(bad), ["tap"], set())
    with pytest.raises(ModelProtocolError):
        parse_decision(json.dumps(good), ["key"], {"enter"})
    with pytest.raises(ModelProtocolError):
        parse_decision('{"action":"key","key":"volume_up","reason":"x","expected":"y"}', ["key"], {"enter"})


async def test_prefix_images_role_headers_extra_and_real_usage():
    captured = []
    async def handle(request):
        captured.append(request)
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"plan":"1. Open settings"}'}}],
                                         "usage": {"prompt_tokens": 20, "completion_tokens": 10}})
    settings = ModelSettings(base_url="https://example.test/provider/v1", model="user-model", api_key="private-key",
                             extra_body={"temperature": 0.1})
    client = ModelClient(settings, httpx.MockTransport(handle))
    try:
        reply = await client.chat("Plan", "Goal", [b"jpeg-test"])
    finally:
        await client.close()
    request = captured[0]
    assert str(request.url) == "https://example.test/provider/v1/chat/completions"
    assert request.headers["Authorization"] == "Bearer private-key"
    body = json.loads(request.content)
    assert body["model"] == "user-model" and body["stream"] is False and body["temperature"] == 0.1
    assert body["messages"][0] == {"role": "system", "content": "Plan"}
    url = body["messages"][1]["content"][1]["image_url"]["url"]
    assert base64.b64decode(url.split(",")[1]) == b"jpeg-test"
    assert reply.usage.total_tokens == 30 and not reply.usage.estimated


async def test_missing_usage_is_explicit_estimate():
    client = ModelClient(ModelSettings(model="local"), httpx.MockTransport(lambda request: httpx.Response(
        200, json={"choices": [{"message": {"content": "{}"}}]})))
    try:
        result = await client.chat("a", "b", [b"image"])
        assert result.usage.estimated and result.usage.total_tokens >= 4096
    finally:
        await client.close()


async def test_truncated_completion_cannot_supply_a_valid_action():
    calls = 0
    def handle(request):
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"choices": [{"finish_reason": "length", "message": {
            "content": '{"action":"tap","x":500,"y":500,"reason":"x","expected":"y"}'}}],
            "usage": {"total_tokens": 123}})
    client = ModelClient(ModelSettings(model="vision"), httpx.MockTransport(handle))
    try:
        with pytest.raises(ModelProtocolError, match="output limit"):
            await client.chat("Choose an action", "Goal")
    finally:
        await client.close()
    assert calls == 1


@pytest.mark.parametrize("finish,fields", [
    ("length", {"content": ""}), ("length", {"content": None}),
    ("content_filter", {}), ("tool_calls", {}), ("function_call", {}),
    ("stop", {"tool_calls": [{"private-key": "secret tool arguments"}]}),
    ("stop", {"function_call": {"name": "private-key"}}),
    ("stop", {"refusal": "private-key provider refusal"}),
    (None, {"refusal": "private-key"}), ("private-key", {}),
    (True, {}), ([], {}), ({"private-key": 1}, {}),
])
async def test_non_normal_completions_are_redacted_and_preserve_real_usage(finish, fields):
    captured = []
    def handle(request):
        captured.append(request)
        return httpx.Response(200, json={"choices": [{"finish_reason": finish,
            "message": {"content": "{}", **fields}}],
            "usage": {"prompt_tokens": 50, "completion_tokens": 70}})
    client = ModelClient(ModelSettings(model="vision"), httpx.MockTransport(handle))
    try:
        with pytest.raises(ModelCompletionError) as caught:
            await client.chat("System", "Goal")
        assert caught.value.usage.total_tokens == 120 and not caught.value.usage.estimated
        assert caught.value.seconds >= 0 and "private-key" not in str(caught.value)
    finally:
        await client.close()
    assert len(captured) == 1


@pytest.mark.parametrize("metadata", [{}, {"finish_reason": None}, {"finish_reason": "stop"}])
async def test_legacy_and_normal_completions_still_require_valid_json(metadata):
    client = ModelClient(ModelSettings(model="vision"), httpx.MockTransport(lambda request: httpx.Response(
        200, json={"choices": [{**metadata, "message": {"content": "{}", "tool_calls": [], "refusal": None}}]})))
    try:
        assert parse_object((await client.chat("System", "Goal")).text) == {}
    finally:
        await client.close()


async def test_truncated_completion_without_usage_is_accounted_as_estimate():
    client = ModelClient(ModelSettings(model="vision", extra_body={"max_completion_tokens": 2048}),
        httpx.MockTransport(lambda request: httpx.Response(
        200, json={"choices": [{"finish_reason": "length", "message": {"content": None}}]})))
    try:
        with pytest.raises(ModelCompletionError) as caught:
            await client.chat("System", "Goal", [b"image"])
        assert caught.value.usage.estimated
        assert caught.value.usage.total_tokens == estimate_tokens("System", "Goal", [b"image"]) + 2048
    finally:
        await client.close()


async def test_completion_limit_omits_mutually_exclusive_legacy_field():
    captured = []
    def handle(request):
        captured.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})
    client = ModelClient(ModelSettings(model="vision", extra_body={"max_completion_tokens": 2048}), httpx.MockTransport(handle))
    try:
        await client.chat("a", "b")
    finally:
        await client.close()
    assert captured[0]["max_completion_tokens"] == 2048 and "max_tokens" not in captured[0]


@pytest.mark.parametrize("value", [True, 0, 5000, "2048"])
def test_completion_limit_has_a_bounded_strict_integer(value):
    with pytest.raises(ValueError):
        ModelSettings(model="vision", extra_body={"max_completion_tokens": value})


@pytest.mark.parametrize("failure", ["http", "timeout", "oversize", "envelope"])
async def test_model_failure_is_redacted_and_never_automatically_retried(failure):
    calls = 0
    def handle(request):
        nonlocal calls
        calls += 1
        if failure == "timeout":
            raise httpx.ReadTimeout("private-key in provider message", request=request)
        if failure == "http":
            return httpx.Response(401, text="private-key in provider response")
        if failure == "oversize":
            return httpx.Response(200, content=b"x" * (1024 * 1024 + 1))
        return httpx.Response(200, json={"private-key": "invalid envelope"})
    client = ModelClient(ModelSettings(model="local", api_key="private-key"), httpx.MockTransport(handle))
    try:
        with pytest.raises(ModelError) as error:
            await client.chat("a", "b")
        assert "private-key" not in str(error.value)
        assert calls == 1
    finally:
        await client.close()
