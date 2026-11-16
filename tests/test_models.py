import dataclasses

import pytest

from cpu_scheduler.models import MLFQConfig, Process, ProcessState, SimulationConfig


class TestProcess:
    def test_fields(self):
        p = Process(pid="P1", arrival_time=2, burst_time=5, priority=3)
        assert p.pid == "P1"
        assert p.arrival_time == 2
        assert p.burst_time == 5
        assert p.priority == 3

    def test_priority_defaults_to_zero(self):
        assert Process("P1", 0, 4).priority == 0

    def test_is_frozen(self):
        p = Process("P1", 0, 4)
        with pytest.raises(dataclasses.FrozenInstanceError):
            p.burst_time = 10


class TestProcessState:
    def test_initial_values(self):
        state = ProcessState(Process("P1", 0, 7))
        assert state.remaining_time == 7
        assert state.accumulated_ready_wait == 0
        assert state.first_start is None
        assert state.completion_time is None
        assert not state.is_finished

    def test_is_finished_when_remaining_zero(self):
        state = ProcessState(Process("P1", 0, 7))
        state.remaining_time = 0
        assert state.is_finished

    def test_pid_delegates_to_process(self):
        state = ProcessState(Process("P1", 0, 7))
        assert state.pid == "P1"


class TestConfig:
    def test_defaults(self):
        config = SimulationConfig()
        assert config.context_switch_cost == 0
        assert config.time_quantum is None
        assert config.aging_interval is None
        assert config.mlfq is None

    def test_mlfq_levels(self):
        mlfq = MLFQConfig(quantums=(4, 8, 16), boost_interval=50)
        assert mlfq.levels == 3

    def test_config_is_frozen(self):
        config = SimulationConfig()
        with pytest.raises(dataclasses.FrozenInstanceError):
            config.context_switch_cost = 5