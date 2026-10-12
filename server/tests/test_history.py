import io
import uuid
import zipfile

import pytest

from android_agent.errors import AgentError
from android_agent.history import EventBus, Redactor, TraceStore


async def test_slow_subscriber_overflow_resets_without_blocking():
    bus = EventBus(queue_size=2)
    async with bus.subscribe() as queue:
        bus.publish()
        bus.publish()
        bus.publish()
        assert queue.qsize() == 1
        assert await queue.get() == {"event": "reset", "revision": 3}
    assert not bus.queues


async def test_trace_export_and_read_cannot_traverse(tmp_path):
    store = TraceStore(tmp_path)
    task_id = uuid.uuid4().hex
    await store.write(task_id, {"event": "started"}, {"id": task_id, "state": "completed"})
    archive = zipfile.ZipFile(io.BytesIO(await store.export(task_id)))
    assert set(archive.namelist()) == {"summary.json", "events.jsonl"}
    for malicious in ("../preferences", "a" * 32 + "/../", "..", "A" * 32):
        with pytest.raises(AgentError):
            await store.read(malicious)
        with pytest.raises(AgentError):
            await store.export(malicious)


async def test_export_rejects_file_symlink(tmp_path):
    store = TraceStore(tmp_path)
    task_id = uuid.uuid4().hex
    await store.write(task_id, {}, {"id": task_id})
    outside = tmp_path / "secret.txt"
    outside.write_text("secret", encoding="utf-8")
    path = store.directory(task_id) / "0001-before.jpg"
    try:
        path.symlink_to(outside)
    except OSError:
        pytest.skip("Host does not allow symlink creation")
    with pytest.raises(AgentError):
        await store.export(task_id)


def test_redaction_is_recursive_and_keeps_usage_fields():
    redactor = Redactor(["private-key"])
    assert redactor.clean({"api_key": "private-key", "total_tokens": 5,
                           "steps": ["contains private-key"]}) == {
        "total_tokens": 5, "steps": ["contains [redacted]"]}
