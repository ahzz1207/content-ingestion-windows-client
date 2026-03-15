from __future__ import annotations

import time


class RefreshGate:
    def __init__(self, *, min_interval_seconds: float) -> None:
        self.min_interval_seconds = min_interval_seconds
        self._last_refresh_at: float | None = None

    def allow_now(self, *, now: float | None = None) -> bool:
        return self.seconds_until_allowed(now=now) <= 0

    def mark(self, *, now: float | None = None) -> None:
        self._last_refresh_at = time.monotonic() if now is None else now

    def seconds_until_allowed(self, *, now: float | None = None) -> float:
        if self._last_refresh_at is None:
            return 0.0
        current = time.monotonic() if now is None else now
        remaining = self.min_interval_seconds - (current - self._last_refresh_at)
        return max(0.0, remaining)
