"""Golden SJF examples: every expected number below is calculated by hand."""

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
    def test_textbook_example(self):
        # P1 0-7 (non-preemptive), then P3 7-8, P2 8-12, P4 12-16.
        processes = [
            Process("P1", 0, 7), Process("P2", 2, 4),
            Process("P3", 4, 1), Process("P4", 5, 4),
        ]
        result = run_simulation("sjf", processes, SimulationConfig())
        assert as_tuples(result.timeline) == [
            (0, 7, K.EXECUTE, "P1"),
            (7, 8, K.EXECUTE, "P3"),
            (8, 12, K.EXECUTE, "P2"),
            (12, 16, K.EXECUTE, "P4"),
        ]
        assert metrics_of(result, "P1") == {"CT": 7, "TAT": 7, "WT": 0, "RT": 0}
        assert metrics_of(result, "P2") == {"CT": 12, "TAT": 10, "WT": 6, "RT": 6}
        assert metrics_of(result, "P3") == {"CT": 8, "TAT": 4, "WT": 3, "RT": 3}
        assert metrics_of(result, "P4") == {"CT": 16, "TAT": 11, "WT": 7, "RT": 7}
        m = result.metrics
        assert m.average_waiting_time == pytest.approx(4.0)
        assert m.average_turnaround_time == pytest.approx(8.0)
        assert m.average_response_time == pytest.approx(4.0)
        assert m.cpu_utilization == pytest.approx(1.0)
        assert m.throughput == pytest.approx(0.25)
        assert m.context_switch_count == 0
        assert m.makespan == 16

    def test_cs_cost_and_idle_gap(self):
        # P1 0-2, CS 2-3, P2 3-4, idle 4-5, CS 5-6, P3 6-8.
        processes = [Process("P1", 0, 2), Process("P2", 1, 1), Process("P3", 5, 2)]
        result = run_simulation("sjf", processes, SimulationConfig(context_switch_cost=1))
        assert as_tuples(result.timeline) == [
            (0, 2, K.EXECUTE, "P1"),
            (2, 3, K.CONTEXT_SWITCH, None),
            (3, 4, K.EXECUTE, "P2"),
            (4, 5, K.IDLE, None),
            (5, 6, K.CONTEXT_SWITCH, None),
            (6, 8, K.EXECUTE, "P3"),
        ]
        assert metrics_of(result, "P1") == {"CT": 2, "TAT": 2, "WT": 0, "RT": 0}
        assert metrics_of(result, "P2") == {"CT": 4, "TAT": 3, "WT": 2, "RT": 2}
        assert metrics_of(result, "P3") == {"CT": 8, "TAT": 3, "WT": 1, "RT": 1}
        m = result.metrics
        assert m.average_waiting_time == pytest.approx(1.0)
        assert m.average_turnaround_time == pytest.approx(8 / 3)
        assert m.cpu_utilization == pytest.approx(0.625)
        assert m.throughput == pytest.approx(0.375)
        assert m.context_switch_count == 2
        assert m.makespan == 8

    def test_equal_bursts_tie_break_by_pid(self):
        processes = [Process("P2", 0, 3), Process("P1", 0, 3)]
        result = run_simulation("sjf", processes, SimulationConfig())
        assert as_tuples(result.timeline) == [
            (0, 3, K.EXECUTE, "P1"),
            (3, 6, K.EXECUTE, "P2"),
        ]

    def test_equal_bursts_tie_break_by_arrival(self):
        processes = [Process("P1", 2, 3), Process("P2", 0, 3)]
        result = run_simulation("sjf", processes, SimulationConfig())
        assert as_tuples(result.timeline) == [
            (0, 3, K.EXECUTE, "P2"),
            (3, 6, K.EXECUTE, "P1"),
        ]

    def test_is_non_preemptive(self):
        # A shorter job arriving mid-burst must wait for P1 to finish.
        processes = [Process("P1", 0, 5), Process("P2", 1, 1)]
        result = run_simulation("sjf", processes, SimulationConfig())
        assert as_tuples(result.timeline) == [
            (0, 5, K.EXECUTE, "P1"),
            (5, 6, K.EXECUTE, "P2"),
        ]
        assert metrics_of(result, "P2") == {"CT": 6, "TAT": 5, "WT": 4, "RT": 4}