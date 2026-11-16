"""Immutable process specification and mutable runtime state."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Process:
    """The user-defined input: lower priority number means higher priority."""

    pid: str
    arrival_time: int
    burst_time: int
    priority: int = 0


@dataclass
class ProcessState:
    """Runtime bookkeeping owned by the engine, kept out of the input model."""

    process: Process
    remaining_time: int = field(init=False)
    accumulated_ready_wait: int = 0
    first_start: int | None = None
    completion_time: int | None = None

    def __post_init__(self) -> None:
        self.remaining_time = self.process.burst_time

    @property
    def pid(self) -> str:
        return self.process.pid

    @property
    def is_finished(self) -> bool:
        return self.remaining_time == 0