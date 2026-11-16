import asyncio
import threading
from typing import Any


class EventBus:
    """Fan-out of project updates to server-sent event subscribers, safe to publish from any thread."""

    def __init__(self) -> None:
        self._subs: dict[str, list[tuple[asyncio.AbstractEventLoop, asyncio.Queue]]] = {}
        self._lock = threading.Lock()

    def subscribe(self, project_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=200)
        with self._lock:
            self._subs.setdefault(project_id, []).append((asyncio.get_running_loop(), q))
        return q

    def unsubscribe(self, project_id: str, q: asyncio.Queue) -> None:
        with self._lock:
            self._subs[project_id] = [(l, x) for (l, x) in self._subs.get(project_id, []) if x is not q]

    def publish(self, project_id: str, event: dict[str, Any]) -> None:
        with self._lock:
            subs = list(self._subs.get(project_id, []))
        for loop, q in subs:
            def _put(q=q) -> None:
                if not q.full():
                    q.put_nowait(event)
            loop.call_soon_threadsafe(_put)
