"""Shortest Job First: non-preemptive, shortest burst among arrived processes.

Tie-break: arrival time, then pid.
"""

from cpu_scheduler.core.policy import SchedulingPolicy
from cpu_scheduler.models.process import ProcessState


class SJFPolicy(SchedulingPolicy):
    name = "sjf"

    def __init__(self) -> None:
        self._ready: list[ProcessState] = []

    def on_arrival(self, state: ProcessState, now: int) -> None:
        self._ready.append(state)

    def pick_next(self, now: int) -> ProcessState | None:
        if not self._ready:
            return None
        best = min(
            self._ready,
            key=lambda s: (s.process.burst_time, s.process.arrival_time, s.pid),
        )
        self._ready.remove(best)
        return best

    def slice_length(self, state: ProcessState, now: int) -> int:
        return state.remaining_time

    def on_slice_end(self, state: ProcessState, now: int) -> None:
        # Non-preemptive: the slice always covers the whole burst.
        pass