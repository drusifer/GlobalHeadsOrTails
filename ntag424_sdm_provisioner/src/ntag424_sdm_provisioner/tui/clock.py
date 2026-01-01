"""Clock abstraction for deterministic testing."""

import threading
import time
from abc import ABC, abstractmethod
from collections.abc import Callable


class Clock(ABC):
    """Abstract clock for time-dependent operations."""

    @abstractmethod
    def sleep(self, seconds: float) -> None:
        """Sleep for specified duration."""

    @abstractmethod
    def schedule(self, delay: float, callback: Callable[[], None]) -> None:
        """Schedule callback after delay."""


class RealClock(Clock):
    """Production clock using real time."""

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)

    def schedule(self, delay: float, callback: Callable[[], None]) -> None:
        timer = threading.Timer(delay, callback)
        timer.start()


class FakeClock(Clock):
    """Test clock with manual time control for deterministic testing."""

    def __init__(self):
        self._time: float = 0.0
        self._scheduled: list[tuple[float, Callable[[], None]]] = []

    def sleep(self, seconds: float) -> None:
        self.advance(seconds)

    def advance(self, seconds: float) -> None:
        """Manually advance time (for tests)."""
        self._time += seconds
        self._run_scheduled()

    def schedule(self, delay: float, callback: Callable[[], None]) -> None:
        when = self._time + delay
        self._scheduled.append((when, callback))
        self._scheduled.sort(key=lambda item: item[0])

    def _run_scheduled(self) -> None:
        """Run all callbacks whose time has come."""
        while self._scheduled and self._scheduled[0][0] <= self._time:
            _, callback = self._scheduled.pop(0)
            callback()

    @property
    def current_time(self) -> float:
        """Get current (fake) time."""
        return self._time
