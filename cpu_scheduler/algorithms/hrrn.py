"""Highest Response Ratio Next: non-preemptive.

ratio = (waiting + burst) / burst, where waiting = now - arrival.
Fractions keep the comparison exact, so mathematically equal ratios really
tie and fall through to arrival time, then pid.
"""

from fractions import Fraction

from cpu_scheduler.core.policy import SchedulingPolicy
from cpu_scheduler.models.process import ProcessState


class HRRNPolicy(SchedulingPolicy):
    name = "hrrn"

    def __init__(self) -> None:
        self._ready: list[ProcessState] = []

    def on_arrival(self, state: ProcessState, now: int) -> None:
        self._ready.append(state)

    def pick_next(self, now: int) -> ProcessState | None:
        if not self._ready:
            return None

        def key(state: ProcessState) -> tuple[Fraction, int, str]:
            wait = now - state.process.arrival_time
            ratio = Fraction(wait + state.process.burst_time, state.process.burst_time)
            return (-ratio, state.process.arrival_time, state.pid)

        best = min(self._ready, key=key)
        self._ready.remove(best)
        return best

    def slice_length(self, state: ProcessState, now: int) -> int:
        return state.remaining_time

    def on_slice_end(self, state: ProcessState, now: int) -> None:
        # Non-preemptive: the slice always covers the whole burst.
        pass