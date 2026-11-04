from collections import deque


class Clock:
    def __init__(
        self, total: float, increment: float, overhead: float, entry_estimate: float = 3.0
    ) -> None:
        self.remaining = total
        self.increment = increment
        self.overhead = overhead
        self.entry_estimate = entry_estimate
        self._samples: deque[float] = deque(maxlen=8)
        self._pending: float | None = None

    def record_entry(self, seconds: float) -> None:
        seconds = max(0.0, seconds)
        self._pending = seconds
        self._samples.append(seconds)

    def expected_entry(self) -> float:
        if not self._samples:
            return self.entry_estimate
        return sum(self._samples) / len(self._samples)

    def expected_overhead(self, typed: bool = True) -> float:
        return self.overhead + (self.expected_entry() if typed else 0.0)

    def spend(self, thinking: float, typed: bool = True) -> None:
        entry = 0.0
        if typed:
            entry = self._pending if self._pending is not None else self.entry_estimate
        self._pending = None
        self.remaining = max(0.0, self.remaining - thinking - self.overhead - entry) + self.increment

    def set(self, seconds: float) -> None:
        self.remaining = max(0.0, seconds)

    def __str__(self) -> str:
        minutes, seconds = divmod(int(self.remaining), 60)
        return f"{minutes}:{seconds:02d}"


def parse_clock(text: str) -> float:
    text = text.strip()
    if ":" in text:
        minutes, seconds = text.split(":", 1)
        return int(minutes) * 60 + float(seconds)
    return float(text)
