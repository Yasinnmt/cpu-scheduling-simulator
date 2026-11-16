"""First-Come, First-Served: non-preemptive, arrival order, ties broken by pid."""

from collections import deque

from cpu_scheduler.core.policy import SchedulingPolicy
from cpu_scheduler.models.process import ProcessState


class FCFSPolicy(SchedulingPolicy):
    name = "fcfs"

    def __init__(self) -> None:
        self._ready: deque[ProcessState] = deque()

    def on_arrival(self, state: ProcessState, now: int) -> None:
        self._ready.append(state)

    def pick_next(self, now: int) -> ProcessState | None:
        return self._ready.popleft() if self._ready else None

    def slice_length(self, state: ProcessState, now: int) -> int:
        return state.remaining_time

    def on_slice_end(self, state: ProcessState, now: int) -> None:
        # The slice always covers the whole burst, so this is never reached
        # with unfinished work.
        pass