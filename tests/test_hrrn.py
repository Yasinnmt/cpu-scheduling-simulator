"""Golden HRRN examples: every expected number below is calculated by hand."""

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
        # t=3: only P2 (ratio 7/6). t=9: P3 9/4 > P4 8/5 > P5 3/2.
        # t=13: P5 7/2 > P4 12/5. Gantt: P1 0-3, P2 3-9, P3 9-13, P5 13-15, P4 15-20.
        processes = [
            Process("P1", 0, 3), Process("P2", 2, 6), Process("P3", 4, 4),
            Process("P4", 6, 5), Process("P5", 8, 2),
        ]
        result = run_simulation("hrrn", processes, SimulationConfig())
        assert as_tuples(result.timeline) == [
            (0, 3, K.EXECUTE, "P1"),
            (3, 9, K.EXECUTE, "P2"),
            (9, 13, K.EXECUTE, "P3"),
            (13, 15, K.EXECUTE, "P5"),
            (15, 20, K.EXECUTE, "P4"),
        ]
        assert metrics_of(result, "P1") == {"CT": 3, "TAT": 3, "WT": 0, "RT": 0}
        assert metrics_of(result, "P2") == {"CT": 9, "TAT": 7, "WT": 1, "RT": 1}
        assert metrics_of(result, "P3") == {"CT": 13, "TAT": 9, "WT": 5, "RT": 5}
        assert metrics_of(result, "P4") == {"CT": 20, "TAT": 14, "WT": 9, "RT": 9}
        assert metrics_of(result, "P5") == {"CT": 15, "TAT": 7, "WT": 5, "RT": 5}
        m = result.metrics
        assert m.average_waiting_time == pytest.approx(4.0)
        assert m.average_turnaround_time == pytest.approx(8.0)
        assert m.cpu_utilization == pytest.approx(1.0)
        assert m.throughput == pytest.approx(0.25)
        assert m.context_switch_count == 0
        assert m.makespan == 20

    def test_short_job_beats_long_job_at_equal_wait(self):
        # At t=2: P3 ratio 3/1 = 3 beats P2 ratio 12/10 = 1.2.
        processes = [Process("P1", 0, 2), Process("P2", 0, 10), Process("P3", 0, 1)]
        result = run_simulation("hrrn", processes, SimulationConfig())
        assert as_tuples(result.timeline) == [
            (0, 2, K.EXECUTE, "P1"),
            (2, 3, K.EXECUTE, "P3"),
            (3, 13, K.EXECUTE, "P2"),
        ]
        assert metrics_of(result, "P2") == {"CT": 13, "TAT": 13, "WT": 3, "RT": 3}
        assert metrics_of(result, "P3") == {"CT": 3, "TAT": 3, "WT": 2, "RT": 2}
        assert result.metrics.average_waiting_time == pytest.approx(5 / 3)

    def test_exact_ratio_ties_use_arrival_then_pid(self):
        # t=0: P1/P2/P4 all ratio 1 -> pid P1. t=4: P2, P3, P4 all ratio 2
        # -> earliest arrival (P2, P4 at 0) -> pid P2. t=8: P3 4 > P4 3.
        processes = [
            Process("P1", 0, 4), Process("P2", 0, 4),
            Process("P3", 2, 2), Process("P4", 0, 4),
        ]
        result = run_simulation("hrrn", processes, SimulationConfig())
        assert as_tuples(result.timeline) == [
            (0, 4, K.EXECUTE, "P1"),
            (4, 8, K.EXECUTE, "P2"),
            (8, 10, K.EXECUTE, "P3"),
            (10, 14, K.EXECUTE, "P4"),
        ]
        assert metrics_of(result, "P3") == {"CT": 10, "TAT": 8, "WT": 6, "RT": 6}
        assert metrics_of(result, "P4") == {"CT": 14, "TAT": 14, "WT": 10, "RT": 10}
        assert result.metrics.average_waiting_time == pytest.approx(5.0)

    def test_cs_cost_and_idle_gap(self):
        # P1 0-2, idle 2-4, CS 4-5, P2 5-8, CS 8-9, P3 9-10.
        processes = [Process("P1", 0, 2), Process("P2", 4, 3), Process("P3", 5, 1)]
        result = run_simulation("hrrn", processes, SimulationConfig(context_switch_cost=1))
        assert as_tuples(result.timeline) == [
            (0, 2, K.EXECUTE, "P1"),
            (2, 4, K.IDLE, None),
            (4, 5, K.CONTEXT_SWITCH, None),
            (5, 8, K.EXECUTE, "P2"),
            (8, 9, K.CONTEXT_SWITCH, None),
            (9, 10, K.EXECUTE, "P3"),
        ]
        assert metrics_of(result, "P2") == {"CT": 8, "TAT": 4, "WT": 1, "RT": 1}
        assert metrics_of(result, "P3") == {"CT": 10, "TAT": 5, "WT": 4, "RT": 4}
        m = result.metrics
        assert m.cpu_utilization == pytest.approx(0.6)
        assert m.context_switch_count == 2
        assert m.makespan == 10

    def test_is_non_preemptive(self):
        processes = [Process("P1", 0, 5), Process("P2", 1, 1)]
        result = run_simulation("hrrn", processes, SimulationConfig())
        assert as_tuples(result.timeline) == [
            (0, 5, K.EXECUTE, "P1"),
            (5, 6, K.EXECUTE, "P2"),
        ]
        assert metrics_of(result, "P2") == {"CT": 6, "TAT": 5, "WT": 4, "RT": 4}