"""Simulation-wide configuration shared by all algorithms."""

from dataclasses import dataclass


@dataclass(frozen=True)
class MLFQConfig:
    """One quantum per queue level; level 0 is the highest queue."""

    quantums: tuple[int, ...]
    boost_interval: int

    @property
    def levels(self) -> int:
        return len(self.quantums)


@dataclass(frozen=True)
class SimulationConfig:
    context_switch_cost: int = 0
    time_quantum: int | None = None
    aging_interval: int | None = None
    mlfq: MLFQConfig | None = None