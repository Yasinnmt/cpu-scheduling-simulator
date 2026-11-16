"""Round Robin: FIFO ready queue with a fixed time quantum.

Boundary convention: a process arriving exactly at a quantum-expiry tick
enters the queue before the preempted process is requeued (the engine admits
arrivals before handling slice ends). If the same process is reselected, no
context switch is charged.
"""

from collections import deque

from cpu_scheduler.core.policy import SchedulingPolicy
from cpu_scheduler.models.process import ProcessState


class RRPolicy(SchedulingPolicy):
    name = "rr"

    def __init__(self, quantum: int) -> None:
        self.quantum = quantum
        self._ready: deque[ProcessState] = deque()

    def on_arrival(self, state: ProcessState, now: int) -> None:
        self._ready.append(state)

    def pick_next(self, now: int) -> ProcessState | None:
        return self._ready.popleft() if self._ready else None

    def slice_length(self, state: ProcessState, now: int) -> int:
        return self.quantum

    def on_slice_end(self, state: ProcessState, now: int) -> None:
        self._ready.append(state)