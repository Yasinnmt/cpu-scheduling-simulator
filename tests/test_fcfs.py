"""Golden FCFS examples: every expected number below is calculated by hand."""

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
    def test_textbook_example_no_overhead(self):
        # P1 0-5, P2 5-8, P3 8-16, P4 16-22.
        processes = [
            Process("P1", 0, 5), Process("P2", 1, 3),
            Process("P3", 2, 8), Process("P4", 3, 6),
        ]
        result = run_simulation("fcfs", processes, SimulationConfig())
        assert as_tuples(result.timeline) == [
            (0, 5, K.EXECUTE, "P1"),
            (5, 8, K.EXECUTE, "P2"),
            (8, 16, K.EXECUTE, "P3"),
            (16, 22, K.EXECUTE, "P4"),
        ]
        assert metrics_of(result, "P1") == {"CT": 5, "TAT": 5, "WT": 0, "RT": 0}
        assert metrics_of(result, "P2") == {"CT": 8, "TAT": 7, "WT": 4, "RT": 4}
        assert metrics_of(result, "P3") == {"CT": 16, "TAT": 14, "WT": 6, "RT": 6}
        assert metrics_of(result, "P4") == {"CT": 22, "TAT": 19, "WT": 13, "RT": 13}
        m = result.metrics
        assert m.average_waiting_time == pytest.approx(5.75)
        assert m.average_turnaround_time == pytest.approx(11.25)
        assert m.average_response_time == pytest.approx(5.75)
        assert m.cpu_utilization == pytest.approx(1.0)
        assert m.throughput == pytest.approx(4 / 22)
        assert m.context_switch_count == 0
        assert m.makespan == 22

    def test_idle_gap_and_context_switches(self):
        # P1 0-3, idle 3-5, CS 5-6, P2 6-8, CS 8-9, P3 9-10.
        processes = [Process("P1", 0, 3), Process("P2", 5, 2), Process("P3", 6, 1)]
        result = run_simulation("fcfs", processes, SimulationConfig(context_switch_cost=1))
        assert as_tuples(result.timeline) == [
            (0, 3, K.EXECUTE, "P1"),
            (3, 5, K.IDLE, None),
            (5, 6, K.CONTEXT_SWITCH, None),
            (6, 8, K.EXECUTE, "P2"),
            (8, 9, K.CONTEXT_SWITCH, None),
            (9, 10, K.EXECUTE, "P3"),
        ]
        assert metrics_of(result, "P1") == {"CT": 3, "TAT": 3, "WT": 0, "RT": 0}
        assert metrics_of(result, "P2") == {"CT": 8, "TAT": 3, "WT": 1, "RT": 1}
        assert metrics_of(result, "P3") == {"CT": 10, "TAT": 4, "WT": 3, "RT": 3}
        m = result.metrics
        assert m.average_waiting_time == pytest.approx(4 / 3)
        assert m.average_turnaround_time == pytest.approx(10 / 3)
        assert m.average_response_time == pytest.approx(4 / 3)
        assert m.cpu_utilization == pytest.approx(0.6)
        assert m.throughput == pytest.approx(0.3)
        assert m.context_switch_count == 2
        assert m.makespan == 10

    def test_simultaneous_arrivals_tie_break_by_pid(self):
        # Input order is P2 first, but equal arrivals must run in pid order.
        processes = [Process("P2", 0, 2), Process("P1", 0, 2)]
        result = run_simulation("fcfs", processes, SimulationConfig())
        assert as_tuples(result.timeline) == [
            (0, 2, K.EXECUTE, "P1"),
            (2, 4, K.EXECUTE, "P2"),
        ]

    def test_simultaneous_arrivals_with_cs_cost(self):
        processes = [Process("P2", 0, 2), Process("P1", 0, 2)]
        result = run_simulation("fcfs", processes, SimulationConfig(context_switch_cost=1))
        assert as_tuples(result.timeline) == [
            (0, 2, K.EXECUTE, "P1"),
            (2, 3, K.CONTEXT_SWITCH, None),
            (3, 5, K.EXECUTE, "P2"),
        ]
        assert metrics_of(result, "P2") == {"CT": 5, "TAT": 5, "WT": 3, "RT": 3}

    def test_single_late_process_no_switch_no_leading_idle(self):
        result = run_simulation(
            "fcfs", [Process("P1", 4, 2)], SimulationConfig(context_switch_cost=3)
        )
        assert as_tuples(result.timeline) == [(4, 6, K.EXECUTE, "P1")]
        assert metrics_of(result, "P1") == {"CT": 6, "TAT": 2, "WT": 0, "RT": 0}
        m = result.metrics
        assert m.cpu_utilization == pytest.approx(1.0)
        assert m.context_switch_count == 0
        assert m.makespan == 2