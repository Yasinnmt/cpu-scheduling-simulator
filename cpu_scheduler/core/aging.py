"""Aging: waiting processes gain priority to prevent starvation.

Effective priority = base priority - (accumulated ready wait // interval).
The wait counter is maintained by the engine and is cumulative across
preemptions. Aging only ever improves priority; the result may go below zero
(which simply means even higher priority), so negative base priorities also
work correctly.
"""

from cpu_scheduler.models.process import ProcessState


class AgingManager:
    def __init__(self, interval: int | None) -> None:
        self.interval = interval

    @property
    def enabled(self) -> bool:
        return self.interval is not None

    def effective_priority(self, state: ProcessState) -> int:
        base = state.process.priority
        if self.interval is None:
            return base
        return base - state.accumulated_ready_wait // self.interval