"""Priority scheduling: lower number = higher priority.

Preemptive variant preempts only on strictly better effective priority;
equal priority keeps the running process in place.
Tie-break: arrival time, then pid. Optional aging improves waiting processes.
"""

from cpu_scheduler.core.aging import AgingManager
from cpu_scheduler.core.policy import SchedulingPolicy
from cpu_scheduler.models.process import ProcessState


class PriorityPolicy(SchedulingPolicy):
    def __init__(self, preemptive: bool, aging_interval: int | None = None) -> None:
        self.preemptive = preemptive
        self.name = "priority" if preemptive else "priority_np"
        self._aging = AgingManager(aging_interval)
        self._ready: list[ProcessState] = []

    def _key(self, state: ProcessState) -> tuple[int, int, str]:
        return (
            self._aging.effective_priority(state),
            state.process.arrival_time,
            state.pid,
        )

    def on_arrival(self, state: ProcessState, now: int) -> None:
        self._ready.append(state)

    def pick_next(self, now: int) -> ProcessState | None:
        if not self._ready:
            return None
        best = min(self._ready, key=self._key)
        self._ready.remove(best)
        return best

    def slice_length(self, state: ProcessState, now: int) -> int:
        return state.remaining_time

    def should_preempt(self, running: ProcessState, now: int) -> bool:
        if not self.preemptive or not self._ready:
            return False
        best = min(self._ready, key=self._key)
        return (
            self._aging.effective_priority(best)
            < self._aging.effective_priority(running)
        )

    def on_preempt(self, state: ProcessState, now: int) -> None:
        self._ready.append(state)

    def on_slice_end(self, state: ProcessState, now: int) -> None:
        # Preemption goes through on_preempt; a slice never expires early.
        pass