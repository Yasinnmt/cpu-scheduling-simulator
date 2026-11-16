"""Validate user input before the engine runs; fail fast with clear messages."""

import numbers

from cpu_scheduler.models.config import MLFQConfig, SimulationConfig
from cpu_scheduler.models.process import Process

VALID_ALGORITHMS = frozenset({
    "fcfs", "sjf", "srtf", "priority", "priority_np", "rr", "hrrn", "mlfq",
})

# Worst case (quantum=1): every executed tick may be followed by a context
# switch, so total ticks <= max_arrival + sum_burst * (1 + cs_cost).
MAX_SIMULATION_TICKS = 1_000_000


class ValidationError(ValueError):
    """Raised when user input is invalid."""


def _check_int(value: object, name: str, minimum: int | None = None) -> None:
    if isinstance(value, bool) or not isinstance(value, numbers.Integral):
        raise ValidationError(f"{name} must be an integer, got {value!r}")
    if minimum is not None and value < minimum:
        raise ValidationError(f"{name} must be >= {minimum}, got {value}")


def validate_processes(processes: list[Process]) -> None:
    if not processes:
        raise ValidationError("process list is empty")
    seen: set[str] = set()
    for p in processes:
        if not isinstance(p, Process):
            raise ValidationError(f"expected Process, got {type(p).__name__}")
        if not isinstance(p.pid, str) or not p.pid.strip():
            raise ValidationError(f"process id must be a non-empty string, got {p.pid!r}")
        if p.pid in seen:
            raise ValidationError(f"duplicate process id: {p.pid!r}")
        seen.add(p.pid)
        _check_int(p.arrival_time, f"{p.pid}.arrival_time", minimum=0)
        _check_int(p.burst_time, f"{p.pid}.burst_time", minimum=1)
        _check_int(p.priority, f"{p.pid}.priority")


def validate_config(config: SimulationConfig) -> None:
    if not isinstance(config, SimulationConfig):
        raise ValidationError("config must be a SimulationConfig")
    _check_int(config.context_switch_cost, "context_switch_cost", minimum=0)
    if config.time_quantum is not None:
        _check_int(config.time_quantum, "time_quantum", minimum=1)
    if config.aging_interval is not None:
        _check_int(config.aging_interval, "aging_interval", minimum=1)
    if config.mlfq is not None:
        mlfq = config.mlfq
        if not isinstance(mlfq, MLFQConfig):
            raise ValidationError("mlfq must be an MLFQConfig")
        if not mlfq.quantums:
            raise ValidationError("mlfq.quantums must define at least one queue level")
        for i, q in enumerate(mlfq.quantums):
            _check_int(q, f"mlfq.quantums[{i}]", minimum=1)
        _check_int(mlfq.boost_interval, "mlfq.boost_interval", minimum=1)


def validate_simulation_inputs(
    algorithm: str,
    processes: list[Process],
    config: SimulationConfig,
) -> None:
    if algorithm not in VALID_ALGORITHMS:
        raise ValidationError(
            f"unknown algorithm {algorithm!r}; valid: {sorted(VALID_ALGORITHMS)}"
        )
    validate_processes(processes)
    validate_config(config)
    if algorithm == "rr" and config.time_quantum is None:
        raise ValidationError("round robin requires time_quantum")
    if algorithm == "mlfq" and config.mlfq is None:
        raise ValidationError("mlfq requires an MLFQConfig (quantums + boost_interval)")
    horizon = max(p.arrival_time for p in processes) + sum(
        p.burst_time for p in processes
    ) * (1 + config.context_switch_cost)
    if horizon > MAX_SIMULATION_TICKS:
        raise ValidationError(
            f"workload too large for the tick engine "
            f"(estimated {horizon} ticks, max {MAX_SIMULATION_TICKS})"
        )