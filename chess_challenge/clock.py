class Clock:
    def __init__(self, total: float, increment: float, overhead: float) -> None:
        self.remaining = total
        self.increment = increment
        self.overhead = overhead

    def spend(self, thinking: float) -> None:
        self.remaining = max(0.0, self.remaining - thinking - self.overhead) + self.increment

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
