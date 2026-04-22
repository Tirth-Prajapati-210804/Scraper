from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Callable
from threading import Lock
from time import monotonic


class SlidingWindowRateLimiter:
    def __init__(self) -> None:
        self._entries: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def _prune(self, key: str, window_seconds: int, now: float) -> deque[float]:
        attempts = self._entries[key]
        cutoff = now - window_seconds
        while attempts and attempts[0] <= cutoff:
            attempts.popleft()
        return attempts

    def retry_after(self, key: str, limit: int, window_seconds: int) -> int:
        now = monotonic()
        with self._lock:
            attempts = self._prune(key, window_seconds, now)
            if len(attempts) >= limit:
                return max(1, int(window_seconds - (now - attempts[0])))
            return 0

    def add(self, key: str) -> None:
        now = monotonic()
        with self._lock:
            self._entries[key].append(now)

    def hit(self, key: str, limit: int, window_seconds: int) -> int:
        retry_after = self.retry_after(key, limit, window_seconds)
        if retry_after:
            return retry_after
        self.add(key)
        return 0

    def reset(self, key: str) -> None:
        with self._lock:
            self._entries.pop(key, None)


def build_rate_limit_key(scope: str, *parts: object) -> str:
    safe_parts = [str(part).strip().lower() for part in parts if str(part).strip()]
    return ":".join([scope, *safe_parts])


def unwrap_client_host(forwarded_for: str | None, fallback: Callable[[], str]) -> str:
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return fallback()
