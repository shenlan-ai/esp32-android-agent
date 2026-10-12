import json

import pytest
from pydantic import ValidationError

from android_agent.errors import DeviceError
from android_agent.provision import UsbProvision, provision_board

KEY, BOARD = "a" * 64, "001122aabbcc"


class FakeConfigSerial:
    chip = "esp32s3"
    protocol = "android-agent-usb-v1"
    accepted = True
    closed = False

    def __init__(self, **kwargs):
        self.requests = []

    def open(self):
        pass

    def reset_input_buffer(self):
        pass

    def close(self):
        self.closed = True

    def write(self, data):
        self.requests.append(json.loads(data))
        return len(data)

    def read_until(self, *args, **kwargs):
        request = self.requests[-1]
        return (json.dumps({"v": 1, "id": request["id"], "chip": self.chip, "protocol": self.protocol,
                            "board_id": BOARD, "status": "config" if request["op"] == "get_config"
                            else "configured" if self.accepted else "error"}) + "\n").encode()


def configuration(**extra):
    return UsbProvision.model_validate({"port": "COM9", "ssid": "WiFi", "password": "password123",
                                        "host": "192.168.1.20", **extra})


def test_configuration_checks_identity_and_does_not_echo_credentials(monkeypatch):
    monkeypatch.setattr("android_agent.provision.time.sleep", lambda _: None)
    device = FakeConfigSerial()
    result = provision_board(configuration(), KEY, 8891, factory=lambda **kw: device)
    assert result == BOARD and device.closed
    assert device.dtr is False and device.rts is False
    assert [r["op"] for r in device.requests] == ["get_config", "configure"]
    assert device.requests[1]["password"] == "password123" and device.requests[1]["token"] == KEY
    assert "password123" not in repr(configuration())


@pytest.mark.parametrize("chip,protocol", [("esp32", "android-agent-usb-v1"), ("esp32s3", "other")])
def test_other_firmware_is_not_written(chip, protocol, monkeypatch):
    monkeypatch.setattr("android_agent.provision.time.sleep", lambda _: None)
    device = FakeConfigSerial()
    device.chip, device.protocol = chip, protocol
    with pytest.raises(DeviceError, match="no configuration was written"):
        provision_board(configuration(), KEY, 8891, factory=lambda **kw: device)
    assert len(device.requests) == 1 and device.closed


@pytest.mark.parametrize("extra", [{"host": "127.0.0.1"}, {"host": "0.0.0.0"}, {"host": "192.168.1.20:8891"},
                                  {"host": "224.1.2.3"}, {"ssid": "中" * 11}, {"password": "short"},
                                  {"password": "a" * 64}, {"ssid": "wifi\n"}])
def test_invalid_network_config_rejected(extra):
    with pytest.raises(ValidationError):
        configuration(**extra)


def test_configuration_rejection_redacts_error(monkeypatch):
    monkeypatch.setattr("android_agent.provision.time.sleep", lambda _: None)
    device = FakeConfigSerial()
    device.accepted = False
    with pytest.raises(DeviceError) as raised:
        provision_board(configuration(), KEY, 8891, factory=lambda **kw: device)
    assert KEY not in str(raised.value) and "password123" not in str(raised.value)
    assert device.closed and len(device.requests) == 2


def test_fragmented_cdc_response_preserves_partial_line(monkeypatch):
    monkeypatch.setattr("android_agent.provision.time.sleep", lambda _: None)

    class Fragmented(FakeConfigSerial):
        pending = b""

        def read_until(self, *args, **kwargs):
            if not self.pending:
                self.pending = super().read_until(*args, **kwargs)
            chunk, self.pending = self.pending[:17], self.pending[17:]
            return chunk

    device = Fragmented()
    assert provision_board(configuration(), KEY, 8891, factory=lambda **kw: device) == BOARD
    assert len(device.requests) == 2
