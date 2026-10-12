from __future__ import annotations

import asyncio
import io
import json
import re
import zipfile
from contextlib import asynccontextmanager
from pathlib import Path

from .errors import AgentError


class Redactor:
    def __init__(self, secrets=()):
        self.secrets = sorted({s for s in secrets if s}, key=len, reverse=True)

    def clean(self, value):
        if isinstance(value, str):
            for secret in self.secrets:
                value = value.replace(secret, "[redacted]")
            return value
        if isinstance(value, list):
            return [self.clean(v) for v in value]
        if isinstance(value, dict):
            return {k: self.clean(v) for k, v in value.items()
                    if k not in {"api_key", "access_token", "pair_code"}}
        return value


class EventBus:
    def __init__(self, queue_size: int = 16):
        self.queue_size = queue_size
        self.revision = 0
        self.queues: set[asyncio.Queue] = set()

    def publish(self) -> None:
        self.revision += 1
        for queue in tuple(self.queues):
            kind = "changed"
            if queue.full():
                while not queue.empty():
                    queue.get_nowait()
                kind = "reset"
            queue.put_nowait({"event": kind, "revision": self.revision})

    @asynccontextmanager
    async def subscribe(self):
        if len(self.queues) >= 32:
            raise AgentError("Too many event subscribers; close unused browser tabs")
        queue = asyncio.Queue(maxsize=self.queue_size)
        self.queues.add(queue)
        try:
            yield queue
        finally:
            self.queues.discard(queue)


class TraceStore:
    def __init__(self, directory: Path):
        self.root = (directory / "tasks").resolve()
        self._lock = asyncio.Lock()

    def directory(self, task_id: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{32}", task_id):
            raise AgentError("Invalid task identifier")
        path = self.root / task_id
        if path.is_symlink() or path.resolve().parent != self.root:
            raise AgentError("Task path is outside the history directory")
        return path

    def file(self, directory: Path, name: str) -> Path:
        path = directory / name
        if path.is_symlink() or path.resolve().parent != directory.resolve():
            raise AgentError("Unsafe history file path")
        return path

    async def _work(self, function, *args):
        async with self._lock:
            task = asyncio.create_task(asyncio.to_thread(function, *args))
            try:
                return await asyncio.shield(task)
            except asyncio.CancelledError:
                await task  # Finish a bounded write before another thread touches the trace.
                raise
            except OSError as exc:
                raise AgentError("Cannot access local task history; check data directory permissions") from exc

    async def write(self, task_id: str, event: dict, snapshot: dict,
                    images: dict[str, bytes] | None = None) -> None:
        def save():
            directory = self.directory(task_id)
            directory.mkdir(parents=True, exist_ok=True)
            with self.file(directory, "events.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(event, ensure_ascii=False) + "\n")
            temp = self.file(directory, "summary.tmp")
            temp.write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")
            temp.replace(self.file(directory, "summary.json"))
            for name, data in (images or {}).items():
                if not re.fullmatch(r"\d{4}-(before|after)\.jpg", name):
                    raise AgentError("Invalid step image name")
                self.file(directory, name).write_bytes(data)
        await self._work(save)

    async def read(self, task_id: str) -> dict:
        def load():
            path = self.file(self.directory(task_id), "summary.json")
            if not path.is_file():
                raise AgentError("Task history was not found")
            if path.stat().st_size > 1024 * 1024:
                raise AgentError("Task summary exceeds the size limit")
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except ValueError as exc:
                raise AgentError("Task history is incomplete or invalid") from exc
        return await self._work(load)

    async def list(self) -> list[dict]:
        def load():
            if not self.root.exists():
                return []
            result = []
            for entry in sorted(self.root.iterdir(), key=lambda p: p.name):
                if not re.fullmatch(r"[0-9a-f]{32}", entry.name):
                    continue
                try:
                    directory = self.directory(entry.name)
                    path = self.file(directory, "summary.json")
                    if not path.is_file() or path.stat().st_size > 1024 * 1024:
                        continue
                    item = json.loads(path.read_text(encoding="utf-8"))
                    result.append({k: item.get(k) for k in ("id", "goal", "state", "created_at", "actions", "tokens")})
                except (AgentError, ValueError, OSError):
                    continue
            return sorted(result, key=lambda p: p.get("created_at") or "", reverse=True)[:50]
        return await self._work(load)

    async def export(self, task_id: str) -> bytes:
        def bundle():
            directory = self.directory(task_id)
            if not directory.is_dir():
                raise AgentError("Task history was not found")
            output = io.BytesIO()
            total = 0
            with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
                for entry in directory.iterdir():
                    if not re.fullmatch(r"events\.jsonl|summary\.json|\d{4}-(before|after)\.jpg", entry.name):
                        continue
                    path = self.file(directory, entry.name)
                    if not path.is_file():
                        raise AgentError("Invalid history export entry")
                    total += path.stat().st_size
                    if total > 128 * 1024 * 1024:
                        raise AgentError("History export exceeds 128MB")
                    archive.write(path, arcname=path.name)
            return output.getvalue()
        return await self._work(bundle)
