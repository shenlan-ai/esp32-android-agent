import pytest
from pydantic import SecretStr

from android_agent.config import (
    ConfigStore,
    ModelSettings,
    Preferences,
    PreferencesUpdate,
    RuntimeSettings,
)
from android_agent.errors import AgentError


def test_secret_update_preserves_then_clears(tmp_path):
    store = ConfigStore(tmp_path)
    prefs = Preferences(actor=ModelSettings(model="vision", api_key=SecretStr("private-key")))
    updated = store.update(
        prefs, PreferencesUpdate.model_validate({"actor": {"model": "other", "api_key": ""}})
    )
    assert updated.actor.api_key.get_secret_value() == "private-key"
    assert "private-key" not in str(updated.public())
    assert store.load().actor.api_key.get_secret_value() == "private-key"
    cleared = store.update(
        updated, PreferencesUpdate.model_validate({"actor": {"clear_api_key": True}})
    )
    assert not cleared.actor.api_key.get_secret_value()


def test_remote_binding_requires_token():
    with pytest.raises(AgentError, match="ACCESS_TOKEN"):
        RuntimeSettings(host="0.0.0.0").check_access()


def test_corrupt_configuration_is_not_overwritten(tmp_path):
    path = tmp_path / "preferences.json"
    path.write_text("broken", encoding="utf-8")
    with pytest.raises(AgentError):
        ConfigStore(tmp_path).load()
    assert path.read_text() == "broken"
