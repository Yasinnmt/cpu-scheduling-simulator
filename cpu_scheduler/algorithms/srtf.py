"""Shortest Remaining Time First: preemptive SJF.

Preempts only when a ready process has strictly less remaining time than the
running one; equal remaining time keeps the running process in place.
Tie-break: arrival time, then pid.
"""

from cpu_scheduler.core.policy import SchedulingPolicy
from cpu_scheduler.models.process import ProcessState


class SRTFPolicy(SchedulingPolicy):
    name = "srtf"

    def __init__(self) -> None:
        self._ready: list[ProcessState] = []

    def on_arrival(self, state: ProcessState, now: int) -> None:
        self._ready.append(state)

    def pick_next(self, now: int) -> ProcessState | None:
        if not self._ready:
            return None
        best = min(
            self._ready,
            key=lambda s: (s.remaining_time, s.process.arrival_time, s.pid),
        )
        self._ready.remove(best)
        return best

    def slice_length(self, state: ProcessState, now: int) -> int:
        return state.remaining_time

    def should_preempt(self, running: ProcessState, now: int) -> bool:
        return bool(self._ready) and min(
            s.remaining_time for s in self._ready
        ) < running.remaining_time

    def on_preempt(self, state: ProcessState, now: int) -> None:
        self._ready.append(state)

    def on_slice_end(self, state: ProcessState, now: int) -> None:
        # Preemption goes through on_preempt; a slice never expires early.
        pass