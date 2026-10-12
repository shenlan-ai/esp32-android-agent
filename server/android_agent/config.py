from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from .ble import Calibration
from .errors import AgentError


class ModelSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base_url: str = "http://localhost:8000/v1"
    model: str = ""
    api_key: SecretStr = SecretStr("")
    extra_body: dict = Field(default_factory=dict)

    @field_validator("base_url")
    @classmethod
    def valid_url(cls, value: str) -> str:
        url = urlparse(value)
        if (
            url.scheme not in {"http", "https"}
            or not url.hostname
            or url.username
            or url.password
            or url.query
            or url.fragment
        ):
            raise ValueError("Use an http(s) API base URL without credentials, query or fragment")
        return value.rstrip("/")

    @field_validator("extra_body")
    @classmethod
    def reserved_fields(cls, value: dict) -> dict:
        if {"messages", "model", "stream", "max_tokens"} & value.keys():
            raise ValueError("extra_body cannot override messages, model, stream or max_tokens")
        return value

    def public(self) -> dict:
        return {
            "base_url": self.base_url,
            "model": self.model,
            "api_key_set": bool(self.api_key.get_secret_value()),
            "extra_body": self.extra_body,
        }


class Preferences(BaseModel):
    model_config = ConfigDict(extra="forbid")
    serial: str | None = None
    actor: ModelSettings = Field(default_factory=ModelSettings)
    planner: ModelSettings = Field(default_factory=ModelSettings)
    max_steps: int = Field(40, ge=1, le=200)
    max_seconds: int = Field(600, ge=10, le=7200)
    max_failures: int = Field(3, ge=1, le=10)
    max_total_tokens: int = Field(100000, ge=1000, le=2000000)
    save_screenshots: bool = False
    ble_calibrations: dict[str, Calibration] = Field(default_factory=dict)

    def public(self) -> dict:
        data = self.model_dump(exclude={"actor", "planner"})
        return {**data, "actor": self.actor.public(), "planner": self.planner.public()}


class ModelUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base_url: str | None = None
    model: str | None = Field(None, max_length=200)
    api_key: SecretStr | None = None
    clear_api_key: bool = False
    extra_body: dict | None = None


class PreferencesUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    actor: ModelUpdate | None = None
    planner: ModelUpdate | None = None
    max_steps: int | None = Field(None, ge=1, le=200)
    max_seconds: int | None = Field(None, ge=10, le=7200)
    max_failures: int | None = Field(None, ge=1, le=10)
    max_total_tokens: int | None = Field(None, ge=1000, le=2000000)
    save_screenshots: bool | None = None


class RuntimeSettings(BaseModel):
    data_dir: Path = Field(default_factory=lambda: Path.home() / ".esp32-android-agent")
    adb_path: str = "adb"
    host: str = "127.0.0.1"
    port: int = Field(8890, ge=1, le=65535)
    access_token: SecretStr = SecretStr("")
    command_timeout: float = 10
    preview_interval: float = 0.8

    @property
    def local_only(self) -> bool:
        return self.host in {"127.0.0.1", "localhost", "::1"}

    @classmethod
    def from_env(cls) -> RuntimeSettings:
        values = {
            "data_dir": os.getenv("ANDROID_AGENT_DATA", str(Path.home() / ".esp32-android-agent")),
            "adb_path": os.getenv("ADB_PATH", "adb"),
            "host": os.getenv("ANDROID_AGENT_HOST", "127.0.0.1"),
            "port": int(os.getenv("ANDROID_AGENT_PORT", "8890")),
            "access_token": os.getenv("ANDROID_AGENT_ACCESS_TOKEN", ""),
        }
        settings = cls(**values)
        settings.check_access()
        return settings

    def check_access(self) -> None:
        if not self.local_only and not self.access_token.get_secret_value():
            raise AgentError("Remote binding requires ANDROID_AGENT_ACCESS_TOKEN")


class ConfigStore:
    def __init__(self, directory: Path):
        self.path = directory / "preferences.json"

    def load(self) -> Preferences:
        try:
            prefs = (
                Preferences.model_validate_json(self.path.read_text(encoding="utf-8"))
                if self.path.exists()
                else Preferences()
            )
        except (OSError, ValueError) as exc:
            raise AgentError(
                "Invalid preferences.json; restore or rename it before restarting"
            ) from exc
        for role in ("actor", "planner"):
            current = getattr(prefs, role)
            updates = {}
            for field, key in (
                ("base_url", "BASE_URL"),
                ("model", "MODEL"),
                ("api_key", "API_KEY"),
            ):
                value = os.getenv(f"{role.upper()}_{key}", os.getenv(f"LLM_{key}"))
                if value is not None:
                    updates[field] = value
            if updates:
                setattr(
                    prefs, role, ModelSettings.model_validate({**current.model_dump(), **updates})
                )
        return prefs

    def save(self, prefs: Preferences) -> None:
        data = prefs.model_dump(mode="json")
        for role in ("actor", "planner"):
            data[role]["api_key"] = getattr(prefs, role).api_key.get_secret_value()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp = tempfile.mkstemp(prefix=".preferences-", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(data, stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temp, 0o600)
            os.replace(temp, self.path)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)

    def update(self, prefs: Preferences, patch: PreferencesUpdate) -> Preferences:
        values = prefs.model_dump()
        for key, value in patch.model_dump(
            exclude_unset=True, exclude={"actor", "planner"}
        ).items():
            if value is not None:
                values[key] = value
        for role in ("actor", "planner"):
            update = getattr(patch, role)
            if update is None:
                continue
            config = getattr(prefs, role).model_dump()
            for key in ("base_url", "model", "extra_body"):
                value = getattr(update, key)
                if value is not None:
                    config[key] = value
            if update.clear_api_key:
                config["api_key"] = ""
            elif update.api_key and update.api_key.get_secret_value():
                config["api_key"] = update.api_key
            values[role] = ModelSettings.model_validate(config)
        changed = Preferences.model_validate(values)
        self.save(changed)
        return changed
