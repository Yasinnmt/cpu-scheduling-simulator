"""Shared interface implemented by every scheduling algorithm.

The engine owns the clock, the CPU, and timeline recording; a policy only
makes decisions through these hooks.
"""

from abc import ABC, abstractmethod

from cpu_scheduler.models.process import ProcessState


class SchedulingPolicy(ABC):
    name: str = "base"

    @abstractmethod
    def on_arrival(self, state: ProcessState, now: int) -> None:
        """A process reached its arrival time; put it in the ready structure."""

    @abstractmethod
    def pick_next(self, now: int) -> ProcessState | None:
        """Choose the next process to run (removes it from the ready structure)."""

    @abstractmethod
    def slice_length(self, state: ProcessState, now: int) -> int:
        """How many ticks the dispatched process may run before a decision point."""

    @abstractmethod
    def on_slice_end(self, state: ProcessState, now: int) -> None:
        """The slice expired while the process still has work; requeue it."""

    def should_preempt(self, running: ProcessState, now: int) -> bool:
        return False

    def on_preempt(self, state: ProcessState, now: int) -> None:
        # Default: requeue like a slice end. MLFQ overrides this (no demotion).
        self.on_slice_end(state, now)

    def on_tick(self, now: int) -> None:
        """Per-tick hook for aging and MLFQ priority boosting."""