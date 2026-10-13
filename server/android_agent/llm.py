"""Bounded client for OpenAI-compatible vision Chat Completions.

Request shape adapted from esp32-iphone-agent, Copyright (c) 2026 Henry Yuan.
MIT; see LICENSE and NOTICE. No provider-specific model is required.
"""
from __future__ import annotations

import base64
import json
import math
import re
import time
from dataclasses import dataclass
from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, StrictBool, ValidationError

from .config import ModelSettings
from .errors import AgentError
from .models import Action


class ModelError(AgentError):
    pass


class ModelProtocolError(ModelError):
    pass


def parse_object(text: str) -> dict:
    """Reject duplicate keys, nonfinite numbers and prose outside a JSON object."""
    text = text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if fenced:
        text = fenced[1].strip()

    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = value
        return result

    def invalid_constant(_):
        raise ValueError("nonfinite number")

    try:
        value = json.loads(text, object_pairs_hook=pairs, parse_constant=invalid_constant)
        if not isinstance(value, dict):
            raise ValueError("not an object")
        return value
    except (ValueError, RecursionError) as exc:
        raise ModelProtocolError("Model must return one valid JSON object") from exc


class Plan(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    plan: str = Field(min_length=1, max_length=2000)


class Verdict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    confirmed: StrictBool
    evidence: str = Field(min_length=1, max_length=1000)


class MetaDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    action: Literal["done", "fail", "replan"]
    reason: str = Field(min_length=1, max_length=500)
    answer: str = Field("", max_length=1000)


def parse_decision(text: str, capabilities: list[str], keys: set[str]) -> Action | MetaDecision:
    value = parse_object(text)
    try:
        if value.get("action") in {"done", "fail", "replan"}:
            return MetaDecision.model_validate(value)
        if "frame_id" in value:
            raise ValueError("frame_id belongs to the host")
        action = Action.model_validate(value)
        if (action.action not in capabilities or not action.reason.strip()
                or not action.expected.strip() or (action.action == "key" and action.key not in keys)):
            raise ValueError("missing explanation or unsupported capability")
        return action
    except (ValueError, ValidationError, TypeError) as exc:
        raise ModelProtocolError("Model action is invalid or unavailable for this controller") from exc


@dataclass(frozen=True)
class Usage:
    total_tokens: int
    estimated: bool = False


@dataclass(frozen=True)
class ModelReply:
    text: str
    usage: Usage
    seconds: float


class ModelCompletionError(ModelProtocolError):
    """A received but unusable completion with accountable token consumption."""
    def __init__(self, reason: str, usage: Usage, seconds: float):
        super().__init__(reason)
        self.usage, self.seconds = usage, seconds


def estimate_tokens(system: str, text: str, images: list[bytes], output: str = "") -> int:
    # A conservative execution guard, explicitly not a provider billing formula.
    return math.ceil((len(system) + len(text) + len(output)) / 3) + 4096 * len(images)


class ModelClient:
    def __init__(self, settings: ModelSettings, transport=None):
        if not settings.model.strip():
            raise ModelError("Set and save a vision model name before running a task")
        self.settings = settings.model_copy(deep=True)
        key = settings.api_key.get_secret_value()
        self.http = httpx.AsyncClient(
            timeout=httpx.Timeout(90, connect=10), transport=transport,
            follow_redirects=False, headers={"Authorization": f"Bearer {key}"} if key else {},
        )

    async def chat(self, system: str, text: str, images: list[bytes] | None = None) -> ModelReply:
        images = images or []
        content = [{"type": "text", "text": text}]
        content.extend({"type": "image_url", "image_url": {
            "url": "data:image/jpeg;base64," + base64.b64encode(image).decode("ascii"),
        }} for image in images)
        body = {**self.settings.extra_body, "model": self.settings.model, "stream": False,
                "max_tokens": 1000, "messages": [
                    {"role": "system", "content": system}, {"role": "user", "content": content},
                ]}
        if "max_completion_tokens" in body:
            body.pop("max_tokens")
        started = time.monotonic()
        try:
            # Appending preserves /v1 and other provider base paths (leading '/' would not).
            url = self.settings.base_url.rstrip("/") + "/chat/completions"
            async with self.http.stream("POST", url, json=body) as response:
                if not response.is_success:
                    category = "authentication" if response.status_code in {401, 403} else (
                        "rate limit" if response.status_code == 429 else "endpoint or provider"
                    )
                    raise ModelError(f"Model {category} error (HTTP {response.status_code})")
                data = bytearray()
                async for chunk in response.aiter_bytes():
                    data.extend(chunk)
                    if len(data) > 1024 * 1024:
                        raise ModelProtocolError("Model response exceeds the size limit")
            envelope = json.loads(data)
            choice = envelope["choices"][0]
            message = choice["message"]
            if not isinstance(message, dict):
                raise ValueError("invalid message")
            text_out = message.get("content")
            provided = envelope.get("usage")
            total = provided.get("total_tokens") if isinstance(provided, dict) else None
            if type(total) is not int or total < 0:
                parts = [provided.get(k) for k in ("prompt_tokens", "completion_tokens")] if isinstance(provided, dict) else []
                total = sum(parts) if len(parts) == 2 and all(type(p) is int and p >= 0 for p in parts) else None
            usage = Usage(total, False) if total is not None else Usage(
                estimate_tokens(system, text, images, text_out if isinstance(text_out, str) else ""), True
            )
            seconds = time.monotonic() - started
            finish = choice.get("finish_reason")
            rejection = ""
            if finish == "length":
                rejection = "Model output limit reached; no action accepted. Review the saved output allowance or model"
            elif finish == "content_filter":
                rejection = "Model completion was filtered; no action accepted"
            elif finish in ("tool_calls", "function_call") or message.get("tool_calls") or message.get("function_call"):
                rejection = "Model returned unsupported tool output; no action accepted"
            elif message.get("refusal"):
                rejection = "Model refused the request; no action accepted"
            elif finish not in (None, "stop"):
                rejection = "Model completion did not end normally; no action accepted"
            if rejection:
                if usage.estimated:
                    allowance = self.settings.extra_body.get("max_completion_tokens", 1000)
                    usage = Usage(max(usage.total_tokens, estimate_tokens(system, text, images) + allowance), True)
                raise ModelCompletionError(rejection, usage, seconds)
            if not isinstance(text_out, str) or len(text_out) > 20000:
                raise ValueError("invalid message")
            return ModelReply(text_out, usage, seconds)
        except httpx.TimeoutException as exc:
            raise ModelError("Model request timed out; check the endpoint before retrying") from exc
        except httpx.HTTPError as exc:
            raise ModelError("Cannot reach model endpoint; check the saved URL and connection") from exc
        except (ValueError, KeyError, IndexError, TypeError, RecursionError) as exc:
            raise ModelProtocolError("Model endpoint returned an invalid completion response") from exc

    async def close(self) -> None:
        await self.http.aclose()
