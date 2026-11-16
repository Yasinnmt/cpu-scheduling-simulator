"""Timeline: the single source of truth produced by the engine.

Entries are contiguous, non-overlapping, and chronological, starting at the
first arrival and ending at the last completion. Metrics and visualization
only read this structure.
"""

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from enum import Enum


class IntervalKind(Enum):
    EXECUTE = "execute"
    IDLE = "idle"
    CONTEXT_SWITCH = "context_switch"


@dataclass(frozen=True)
class TimelineEntry:
    start: int
    end: int
    kind: IntervalKind
    pid: str | None = None

    def __post_init__(self) -> None:
        if self.start < 0:
            raise ValueError("interval start must be >= 0")
        if self.end <= self.start:
            raise ValueError("interval end must be greater than start")
        if self.kind is IntervalKind.EXECUTE:
            if not self.pid:
                raise ValueError("EXECUTE interval requires a pid")
        elif self.pid is not None:
            raise ValueError("only EXECUTE intervals may carry a pid")

    @property
    def duration(self) -> int:
        return self.end - self.start


class Timeline:
    def __init__(self, entries: Iterable[TimelineEntry] = ()) -> None:
        self._entries: list[TimelineEntry] = list(entries)

    def append(self, entry: TimelineEntry) -> None:
        self._entries.append(entry)

    @property
    def entries(self) -> tuple[TimelineEntry, ...]:
        return tuple(self._entries)

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self) -> Iterator[TimelineEntry]:
        return iter(self._entries)

    @property
    def first_start(self) -> int | None:
        return self._entries[0].start if self._entries else None

    @property
    def last_end(self) -> int | None:
        return self._entries[-1].end if self._entries else None

    @property
    def makespan(self) -> int:
        if not self._entries:
            return 0
        return self._entries[-1].end - self._entries[0].start

    def _total(self, kind: IntervalKind) -> int:
        return sum(e.duration for e in self._entries if e.kind is kind)

    @property
    def busy_time(self) -> int:
        return self._total(IntervalKind.EXECUTE)

    @property
    def idle_time(self) -> int:
        return self._total(IntervalKind.IDLE)

    @property
    def context_switch_time(self) -> int:
        return self._total(IntervalKind.CONTEXT_SWITCH)

    @property
    def context_switch_count(self) -> int:
        return sum(1 for e in self._entries if e.kind is IntervalKind.CONTEXT_SWITCH)

    def segments_of(self, pid: str) -> tuple[TimelineEntry, ...]:
        return tuple(
            e for e in self._entries
            if e.kind is IntervalKind.EXECUTE and e.pid == pid
        )

    def first_execution_start(self, pid: str) -> int | None:
        segments = self.segments_of(pid)
        return segments[0].start if segments else None

    def completion_time(self, pid: str) -> int | None:
        segments = self.segments_of(pid)
        return segments[-1].end if segments else None