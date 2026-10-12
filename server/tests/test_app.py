import pytest
from fastapi.testclient import TestClient

from android_agent.app import create_app
from android_agent.config import RuntimeSettings


@pytest.fixture
def client(tmp_path, fake_adb):
    app = create_app(RuntimeSettings(data_dir=tmp_path), fake_adb)
    with TestClient(app, base_url="http://localhost") as client:
        client.headers["X-Agent-CSRF"] = client.get("/api/session").json()["csrf"]
        yield client


def test_manual_flow_needs_no_model(client, fake_adb):
    assert client.get("/").status_code == 200
    assert client.get("/api/devices").json()["devices"][0]["serial"] == "phone1"
    assert client.post("/api/devices/select", json={"serial": "phone1"}).status_code == 200
    response = client.get("/api/frame.png")
    assert response.headers["content-type"] == "image/png"
    result = client.post(
        "/api/action",
        json={
            "action": "tap",
            "x": 1000,
            "y": 1000,
            "frame_id": int(response.headers["X-Frame-Id"]),
        },
    )
    assert result.status_code == 200
    assert ("phone1", ("input", "touchscreen", "tap", "199", "399")) in fake_adb.calls


def test_foreign_origin_is_rejected_before_device(client, fake_adb):
    response = client.post(
        "/api/action", headers={"Origin": "https://foreign.example"}, json={"action": "home"}
    )
    assert response.status_code == 403
    assert not fake_adb.calls


def test_missing_request_token_is_rejected(client):
    client.headers.pop("X-Agent-CSRF")
    assert client.post("/api/stop", json={}).status_code == 403


def test_error_does_not_echo_secret_input(client):
    response = client.post(
        "/api/settings", json={"actor": {"api_key": "secret-key", "unexpected": "x"}}
    )
    assert response.status_code == 422
    assert "secret-key" not in response.text


def test_secret_is_masked_in_all_settings_responses(client):
    response = client.post(
        "/api/settings", json={"actor": {"api_key": "secret-key", "model": "test"}}
    )
    assert response.status_code == 200
    assert response.json()["actor"]["api_key_set"]
    assert "secret-key" not in response.text
    assert "secret-key" not in client.get("/api/settings").text


def test_invalid_text_never_reaches_device(client, fake_adb):
    response = client.post("/api/action", json={"action": "type", "text": "中文"})
    assert response.status_code == 422
    assert not fake_adb.calls
