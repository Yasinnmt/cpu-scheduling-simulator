"""Golden Round Robin examples: every expected number below is calculated by hand."""

import pytest

from cpu_scheduler.core.scheduler import run_simulation
from cpu_scheduler.models import IntervalKind as K
from cpu_scheduler.models import Process, SimulationConfig


def metrics_of(result, pid):
    frame = result.metrics.per_process
    row = frame.loc[frame["pid"] == pid].iloc[0]
    return {
        "CT": int(row["completion_time"]),
        "TAT": int(row["turnaround_time"]),
        "WT": int(row["waiting_time"]),
        "RT": int(row["response_time"]),
    }


def as_tuples(timeline):
    return [(e.start, e.end, e.kind, e.pid) for e in timeline]


class TestGoldenExamples:
    def test_textbook_example_quantum_2(self):
        # P1 0-2, P2 2-4, P3 4-5, P1 5-7, P2 7-8, P1 8-9.
        processes = [Process("P1", 0, 5), Process("P2", 1, 3), Process("P3", 2, 1)]
        result = run_simulation("rr", processes, SimulationConfig(time_quantum=2))
        assert as_tuples(result.timeline) == [
            (0, 2, K.EXECUTE, "P1"),
            (2, 4, K.EXECUTE, "P2"),
            (4, 5, K.EXECUTE, "P3"),
            (5, 7, K.EXECUTE, "P1"),
            (7, 8, K.EXECUTE, "P2"),
            (8, 9, K.EXECUTE, "P1"),
        ]
        assert metrics_of(result, "P1") == {"CT": 9, "TAT": 9, "WT": 4, "RT": 0}
        assert metrics_of(result, "P2") == {"CT": 8, "TAT": 7, "WT": 4, "RT": 1}
        assert metrics_of(result, "P3") == {"CT": 5, "TAT": 3, "WT": 2, "RT": 2}
        m = result.metrics
        assert m.average_waiting_time == pytest.approx(10 / 3)
        assert m.average_turnaround_time == pytest.approx(19 / 3)
        assert m.average_response_time == pytest.approx(1.0)
        assert m.cpu_utilization == pytest.approx(1.0)
        assert m.context_switch_count == 0
        assert m.makespan == 9

    def test_arrival_at_quantum_boundary_enters_before_requeue(self):
        # P2 arrives exactly at t=2 when P1's quantum expires: P2 runs first.
        processes = [Process("P1", 0, 4), Process("P2", 2, 2)]
        result = run_simulation("rr", processes, SimulationConfig(time_quantum=2))
        assert as_tuples(result.timeline) == [
            (0, 2, K.EXECUTE, "P1"),
            (2, 4, K.EXECUTE, "P2"),
            (4, 6, K.EXECUTE, "P1"),
        ]
        assert metrics_of(result, "P1") == {"CT": 6, "TAT": 6, "WT": 2, "RT": 0}
        assert metrics_of(result, "P2") == {"CT": 4, "TAT": 2, "WT": 0, "RT": 0}

    def test_single_process_no_self_switch(self):
        # Quantum expires twice, but the same process continues: one merged
        # interval and zero context switches despite cs_cost=3.
        result = run_simulation(
            "rr", [Process("P1", 0, 5)], SimulationConfig(time_quantum=2, context_switch_cost=3)
        )
        assert as_tuples(result.timeline) == [(0, 5, K.EXECUTE, "P1")]
        assert metrics_of(result, "P1") == {"CT": 5, "TAT": 5, "WT": 0, "RT": 0}
        assert result.metrics.context_switch_count == 0
        assert result.metrics.cpu_utilization == pytest.approx(1.0)

    def test_with_cs_overhead(self):
        # P1 0-2, CS 2-3, P2 3-5, CS 5-6, P1 6-8, CS 8-9, P2 9-10.
        processes = [Process("P1", 0, 4), Process("P2", 0, 3)]
        result = run_simulation(
            "rr", processes, SimulationConfig(time_quantum=2, context_switch_cost=1)
        )
        assert as_tuples(result.timeline) == [
            (0, 2, K.EXECUTE, "P1"),
            (2, 3, K.CONTEXT_SWITCH, None),
            (3, 5, K.EXECUTE, "P2"),
            (5, 6, K.CONTEXT_SWITCH, None),
            (6, 8, K.EXECUTE, "P1"),
            (8, 9, K.CONTEXT_SWITCH, None),
            (9, 10, K.EXECUTE, "P2"),
        ]
        assert metrics_of(result, "P1") == {"CT": 8, "TAT": 8, "WT": 4, "RT": 0}
        assert metrics_of(result, "P2") == {"CT": 10, "TAT": 10, "WT": 7, "RT": 3}
        m = result.metrics
        assert m.average_waiting_time == pytest.approx(5.5)
        assert m.cpu_utilization == pytest.approx(0.7)
        assert m.context_switch_count == 3
        assert m.makespan == 10

    def test_quantum_larger_than_burst_behaves_like_fcfs(self):
        processes = [Process("P1", 0, 2), Process("P2", 1, 3)]
        result = run_simulation("rr", processes, SimulationConfig(time_quantum=10))
        assert as_tuples(result.timeline) == [
            (0, 2, K.EXECUTE, "P1"),
            (2, 5, K.EXECUTE, "P2"),
        ]
        assert metrics_of(result, "P2") == {"CT": 5, "TAT": 4, "WT": 1, "RT": 1}
        assert result.metrics.context_switch_count == 0

    def test_quantum_1_alternates(self):
        processes = [Process("P1", 0, 2), Process("P2", 0, 2)]
        result = run_simulation("rr", processes, SimulationConfig(time_quantum=1))
        assert as_tuples(result.timeline) == [
            (0, 1, K.EXECUTE, "P1"),
            (1, 2, K.EXECUTE, "P2"),
            (2, 3, K.EXECUTE, "P1"),
            (3, 4, K.EXECUTE, "P2"),
        ]
        assert metrics_of(result, "P1") == {"CT": 3, "TAT": 3, "WT": 1, "RT": 0}
        assert metrics_of(result, "P2") == {"CT": 4, "TAT": 4, "WT": 2, "RT": 1}

    def test_idle_gap_with_cs_cost(self):
        # P1 0-2, idle 2-5, CS 5-6, P2 6-8.
        processes = [Process("P1", 0, 2), Process("P2", 5, 2)]
        result = run_simulation(
            "rr", processes, SimulationConfig(time_quantum=1, context_switch_cost=1)
        )
        assert as_tuples(result.timeline) == [
            (0, 2, K.EXECUTE, "P1"),
            (2, 5, K.IDLE, None),
            (5, 6, K.CONTEXT_SWITCH, None),
            (6, 8, K.EXECUTE, "P2"),
        ]
        assert metrics_of(result, "P2") == {"CT": 8, "TAT": 3, "WT": 1, "RT": 1}
        assert result.metrics.cpu_utilization == pytest.approx(0.5)
        assert result.metrics.context_switch_count == 1