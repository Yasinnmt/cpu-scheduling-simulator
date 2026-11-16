"""Public facade: validate inputs, run the engine, compute metrics."""

from collections.abc import Callable
from dataclasses import dataclass

from cpu_scheduler.algorithms.fcfs import FCFSPolicy
from cpu_scheduler.algorithms.hrrn import HRRNPolicy
from cpu_scheduler.algorithms.mlfq import MLFQPolicy
from cpu_scheduler.algorithms.priority import PriorityPolicy
from cpu_scheduler.algorithms.round_robin import RRPolicy
from cpu_scheduler.algorithms.sjf import SJFPolicy
from cpu_scheduler.algorithms.srtf import SRTFPolicy
from cpu_scheduler.core.engine import SimulationEngine
from cpu_scheduler.core.policy import SchedulingPolicy
from cpu_scheduler.metrics.calculator import MetricsCalculator, MetricsReport
from cpu_scheduler.models.config import SimulationConfig
from cpu_scheduler.models.process import Process
from cpu_scheduler.models.timeline import Timeline
from cpu_scheduler.validation import validate_simulation_inputs

_POLICIES: dict[str, Callable[[SimulationConfig], SchedulingPolicy]] = {
    "fcfs": lambda config: FCFSPolicy(),
    "sjf": lambda config: SJFPolicy(),
    "srtf": lambda config: SRTFPolicy(),
    "priority": lambda config: PriorityPolicy(True, config.aging_interval),
    "priority_np": lambda config: PriorityPolicy(False, config.aging_interval),
    "rr": lambda config: RRPolicy(config.time_quantum),
    "hrrn": lambda config: HRRNPolicy(),
    "mlfq": lambda config: MLFQPolicy(config.mlfq),
}


@dataclass(frozen=True)
class SimulationResult:
    algorithm: str
    timeline: Timeline
    metrics: MetricsReport


def run_simulation(
    algorithm: str,
    processes: list[Process],
    config: SimulationConfig,
) -> SimulationResult:
    validate_simulation_inputs(algorithm, processes, config)
    policy = _POLICIES[algorithm](config)
    timeline = SimulationEngine(policy, config).run(processes)
    metrics = MetricsCalculator.compute(processes, timeline)
    return SimulationResult(algorithm, timeline, metrics)