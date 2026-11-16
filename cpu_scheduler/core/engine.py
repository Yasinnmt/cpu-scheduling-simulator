"""Tick-based simulation engine, independent of any specific algorithm.

Order of operations at every tick t (the documented scheduling policy):
1. admit arrivals at t, 2. aging/boost hook, 3. slice-end handling,
4. preemption check, 5. dispatch (inserting a context switch if needed),
6. record the activity of [t, t+1), 7. accumulate ready-queue waiting time.

The timeline starts at the first arrival (no leading idle) and context
switches are atomic: arrivals during a switch are considered at the next tick.
"""

from cpu_scheduler.core.context_switch import ContextSwitchManager
from cpu_scheduler.core.policy import SchedulingPolicy
from cpu_scheduler.models.config import SimulationConfig
from cpu_scheduler.models.process import Process, ProcessState
from cpu_scheduler.models.timeline import IntervalKind, Timeline, TimelineEntry


class SimulationEngine:
    def __init__(self, policy: SchedulingPolicy, config: SimulationConfig) -> None:
        self.policy = policy
        self.config = config
        self.states: dict[str, ProcessState] = {}
        self._cs = ContextSwitchManager(config.context_switch_cost)
        self._running: ProcessState | None = None
        self._slice_remaining = 0
        self._cs_remaining = 0
        self._cs_next: ProcessState | None = None
        self._last_pid: str | None = None
        self._unfinished = 0
        self._timeline = Timeline()
        self._rec_kind: IntervalKind | None = None
        self._rec_pid: str | None = None
        self._rec_start = 0

    def run(self, processes: list[Process]) -> Timeline:
        ordered = sorted(processes, key=lambda p: (p.arrival_time, p.pid))
        self.states = {p.pid: ProcessState(p) for p in ordered}
        arrivals: dict[int, list[ProcessState]] = {}
        for state in self.states.values():
            arrivals.setdefault(state.process.arrival_time, []).append(state)
        now = ordered[0].arrival_time
        self._rec_start = now
        self._unfinished = len(ordered)
        while self._unfinished > 0:
            self._tick(now, arrivals.get(now, ()))
            now += 1
        self._flush(now)
        return self._timeline

    def _tick(self, now: int, arriving: list[ProcessState]) -> None:
        for state in arriving:
            self.policy.on_arrival(state, now)
        self.policy.on_tick(now)

        if self._running is not None and self._slice_remaining == 0:
            self.policy.on_slice_end(self._running, now)
            self._running = None
        if self._running is not None and self.policy.should_preempt(self._running, now):
            self.policy.on_preempt(self._running, now)
            self._running = None

        if self._running is None and self._cs_remaining == 0:
            candidate = self.policy.pick_next(now)
            if candidate is not None:
                if self._cs.needs_switch(self._last_pid, candidate.pid):
                    self._cs_remaining = self._cs.cost
                    self._cs_next = candidate
                else:
                    self._start_execution(candidate, now)

        if self._cs_remaining > 0:
            self._record(IntervalKind.CONTEXT_SWITCH, None, now)
            self._cs_remaining -= 1
            if self._cs_remaining == 0:
                assert self._cs_next is not None
                self._start_execution(self._cs_next, now + 1)
                self._cs_next = None
        elif self._running is not None:
            self._record(IntervalKind.EXECUTE, self._running.pid, now)
            self._running.remaining_time -= 1
            self._slice_remaining -= 1
            if self._running.remaining_time == 0:
                self._running.completion_time = now + 1
                self._running = None
                self._unfinished -= 1
        else:
            self._record(IntervalKind.IDLE, None, now)

        for state in self.states.values():
            if (
                state.process.arrival_time <= now
                and not state.is_finished
                and state is not self._running
                and state is not self._cs_next
            ):
                state.accumulated_ready_wait += 1

    def _start_execution(self, state: ProcessState, now: int) -> None:
        self._running = state
        self._slice_remaining = self.policy.slice_length(state, now)
        if state.first_start is None:
            state.first_start = now
        self._last_pid = state.pid

    def _record(self, kind: IntervalKind, pid: str | None, now: int) -> None:
        if kind is self._rec_kind and pid == self._rec_pid:
            return
        self._flush(now)
        self._rec_kind, self._rec_pid, self._rec_start = kind, pid, now

    def _flush(self, now: int) -> None:
        if self._rec_kind is not None:
            self._timeline.append(
                TimelineEntry(self._rec_start, now, self._rec_kind, self._rec_pid)
            )
            self._rec_kind = None