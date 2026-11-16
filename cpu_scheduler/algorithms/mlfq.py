"""Multilevel Feedback Queue.

- Level 0 is the highest queue; new processes enter level 0.
- Each level is FIFO with its own quantum; using a full quantum demotes one
  level (the bottom level keeps its queue).
- A process in a higher queue preempts a lower-queue runner; preemption does
  not demote (the process returns to the tail of its own queue).
- Every boost_interval ticks (absolute time) all waiting processes move to
  level 0, preserving FIFO order level by level. The running process keeps
  its level for the current slice, so a boost can immediately preempt it if
  it runs below level 0.
- Finishing exactly at quantum end is completion, not demotion (the engine
  never calls on_slice_end for completed processes).
"""

from collections import deque

from cpu_scheduler.core.policy import SchedulingPolicy
from cpu_scheduler.models.config import MLFQConfig
from cpu_scheduler.models.process import ProcessState


class MLFQPolicy(SchedulingPolicy):
    name = "mlfq"

    def __init__(self, config: MLFQConfig) -> None:
        self._config = config
        self._queues: list[deque[ProcessState]] = [
            deque() for _ in range(config.levels)
        ]
        self._level: dict[str, int] = {}

    def on_arrival(self, state: ProcessState, now: int) -> None:
        self._level[state.pid] = 0
        self._queues[0].append(state)

    def pick_next(self, now: int) -> ProcessState | None:
        for queue in self._queues:
            if queue:
                return queue.popleft()
        return None

    def slice_length(self, state: ProcessState, now: int) -> int:
        return self._config.quantums[self._level[state.pid]]

    def should_preempt(self, running: ProcessState, now: int) -> bool:
        best = self._highest_ready_level()
        return best is not None and best < self._level[running.pid]

    def _highest_ready_level(self) -> int | None:
        for level, queue in enumerate(self._queues):
            if queue:
                return level
        return None

    def on_preempt(self, state: ProcessState, now: int) -> None:
        self._queues[self._level[state.pid]].append(state)

    def on_slice_end(self, state: ProcessState, now: int) -> None:
        level = min(self._level[state.pid] + 1, self._config.levels - 1)
        self._level[state.pid] = level
        self._queues[level].append(state)

    def on_tick(self, now: int) -> None:
        if now == 0 or now % self._config.boost_interval != 0:
            return
        boosted: list[ProcessState] = []
        for queue in self._queues:
            while queue:
                state = queue.popleft()
                self._level[state.pid] = 0
                boosted.append(state)
        self._queues[0].extend(boosted)