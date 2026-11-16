import pytest

from cpu_scheduler.models import MLFQConfig, Process, SimulationConfig
from cpu_scheduler.validation import (
    VALID_ALGORITHMS,
    ValidationError,
    validate_config,
    validate_processes,
    validate_simulation_inputs,
)


def good_processes():
    return [Process("P1", 0, 5), Process("P2", 2, 3, priority=1)]


def config_for(algorithm):
    if algorithm == "rr":
        return SimulationConfig(time_quantum=2)
    if algorithm == "mlfq":
        return SimulationConfig(mlfq=MLFQConfig(quantums=(2, 4), boost_interval=20))
    return SimulationConfig()


class TestValidInputs:
    @pytest.mark.parametrize("algorithm", sorted(VALID_ALGORITHMS))
    def test_all_algorithms_accept_valid_input(self, algorithm):
        validate_simulation_inputs(algorithm, good_processes(), config_for(algorithm))

    def test_negative_priority_is_allowed(self):
        validate_processes([Process("P1", 0, 5, priority=-2)])

    def test_max_horizon_boundary_is_allowed(self):
        validate_processes([Process("P1", 0, 1_000_000)])
        validate_simulation_inputs("fcfs", [Process("P1", 0, 1_000_000)], SimulationConfig())


class TestInvalidProcesses:
    @pytest.mark.parametrize("processes", [
        [],
        [Process("P1", 0, 5), Process("P1", 1, 2)],
        [Process("", 0, 5)],
        [Process("   ", 0, 5)],
        [Process("P1", -1, 5)],
        [Process("P1", 0, 0)],
        [Process("P1", 0, -3)],
        [Process("P1", 1.5, 5)],
        [Process("P1", 0, "3")],
        [Process("P1", True, 5)],
        [Process("P1", 0, 5, priority=0.5)],
        ["not a process"],
    ])
    def test_rejected(self, processes):
        with pytest.raises(ValidationError):
            validate_processes(processes)


class TestInvalidConfig:
    @pytest.mark.parametrize("config", [
        SimulationConfig(context_switch_cost=-1),
        SimulationConfig(context_switch_cost=0.5),
        SimulationConfig(time_quantum=0),
        SimulationConfig(time_quantum=-2),
        SimulationConfig(aging_interval=0),
        SimulationConfig(mlfq=MLFQConfig(quantums=(), boost_interval=10)),
        SimulationConfig(mlfq=MLFQConfig(quantums=(0,), boost_interval=10)),
        SimulationConfig(mlfq=MLFQConfig(quantums=(2, -1), boost_interval=10)),
        SimulationConfig(mlfq=MLFQConfig(quantums=(2,), boost_interval=0)),
    ])
    def test_rejected(self, config):
        with pytest.raises(ValidationError):
            validate_config(config)


class TestAlgorithmRequirements:
    def test_unknown_algorithm(self):
        with pytest.raises(ValidationError, match="unknown algorithm"):
            validate_simulation_inputs("mlq", good_processes(), SimulationConfig())

    def test_rr_requires_quantum(self):
        with pytest.raises(ValidationError, match="time_quantum"):
            validate_simulation_inputs("rr", good_processes(), SimulationConfig())

    def test_mlfq_requires_config(self):
        with pytest.raises(ValidationError, match="MLFQConfig"):
            validate_simulation_inputs("mlfq", good_processes(), SimulationConfig())

    def test_workload_horizon_guard(self):
        with pytest.raises(ValidationError, match="too large"):
            validate_simulation_inputs(
                "fcfs", [Process("P1", 0, 2_000_000)], SimulationConfig()
            )