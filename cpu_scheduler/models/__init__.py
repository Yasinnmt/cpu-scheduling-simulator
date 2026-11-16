"""Pure data models: no scheduling logic lives here."""

from cpu_scheduler.models.config import MLFQConfig, SimulationConfig
from cpu_scheduler.models.process import Process, ProcessState
from cpu_scheduler.models.timeline import IntervalKind, Timeline, TimelineEntry

__all__ = [
    "MLFQConfig",
    "SimulationConfig",
    "Process",
    "ProcessState",
    "IntervalKind",
    "Timeline",
    "TimelineEntry",
]