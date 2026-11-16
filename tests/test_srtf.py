"""Golden SRTF examples: every expected number below is calculated by hand."""

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
        # P1 0-1, P2 1-5, P4 5-10, P1 10-17, P3 17-26.
        processes = [
            Process("P1", 0, 8), Process("P2", 1, 4),
            Process("P3", 2, 9), Process("P4", 3, 5),
        ]
        result = run_simulation("srtf", processes, SimulationConfig())
        assert as_tuples(result.timeline) == [
            (0, 1, K.EXECUTE, "P1"),
            (1, 5, K.EXECUTE, "P2"),
            (5, 10, K.EXECUTE, "P4"),
            (10, 17, K.EXECUTE, "P1"),
            (17, 26, K.EXECUTE, "P3"),
        ]
        assert metrics_of(result, "P1") == {"CT": 17, "TAT": 17, "WT": 9, "RT": 0}
        assert metrics_of(result, "P2") == {"CT": 5, "TAT": 4, "WT": 0, "RT": 0}
        assert metrics_of(result, "P3") == {"CT": 26, "TAT": 24, "WT": 15, "RT": 15}
        assert metrics_of(result, "P4") == {"CT": 10, "TAT": 7, "WT": 2, "RT": 2}
        m = result.metrics
        assert m.average_waiting_time == pytest.approx(6.5)
        assert m.average_turnaround_time == pytest.approx(13.0)
        assert m.average_response_time == pytest.approx(4.25)
        assert m.cpu_utilization == pytest.approx(1.0)
        assert m.throughput == pytest.approx(4 / 26)
        assert m.context_switch_count == 0
        assert m.makespan == 26

    def test_equal_remaining_does_not_preempt(self):
        # At t=1 P1 has 3 left and P2 arrives with 3: P1 keeps running.
        processes = [Process("P1", 0, 4), Process("P2", 1, 3)]
        result = run_simulation("srtf", processes, SimulationConfig(context_switch_cost=1))
        assert as_tuples(result.timeline) == [
            (0, 4, K.EXECUTE, "P1"),
            (4, 5, K.CONTEXT_SWITCH, None),
            (5, 8, K.EXECUTE, "P2"),
        ]
        assert metrics_of(result, "P1") == {"CT": 4, "TAT": 4, "WT": 0, "RT": 0}
        assert metrics_of(result, "P2") == {"CT": 8, "TAT": 7, "WT": 4, "RT": 4}
        m = result.metrics
        assert m.average_waiting_time == pytest.approx(2.0)
        assert m.cpu_utilization == pytest.approx(0.875)
        assert m.context_switch_count == 1

    def test_preemption_with_cs_overhead(self):
        # P1 0-2, CS 2-3, P2 3-5, CS 5-6, P1 6-10.
        processes = [Process("P1", 0, 6), Process("P2", 2, 2)]
        result = run_simulation("srtf", processes, SimulationConfig(context_switch_cost=1))
        assert as_tuples(result.timeline) == [
            (0, 2, K.EXECUTE, "P1"),
            (2, 3, K.CONTEXT_SWITCH, None),
            (3, 5, K.EXECUTE, "P2"),
            (5, 6, K.CONTEXT_SWITCH, None),
            (6, 10, K.EXECUTE, "P1"),
        ]
        assert metrics_of(result, "P1") == {"CT": 10, "TAT": 10, "WT": 4, "RT": 0}
        assert metrics_of(result, "P2") == {"CT": 5, "TAT": 3, "WT": 1, "RT": 1}
        m = result.metrics
        assert m.average_waiting_time == pytest.approx(2.5)
        assert m.cpu_utilization == pytest.approx(0.8)
        assert m.context_switch_count == 2
        assert m.makespan == 10

    def test_multiple_preemptions(self):
        # P1 0-2, P2 2-4, P3 4-5, P1 5-10 (5 ticks left of its 7-tick burst).
        processes = [Process("P1", 0, 7), Process("P2", 2, 2), Process("P3", 4, 1)]
        result = run_simulation("srtf", processes, SimulationConfig())
        assert as_tuples(result.timeline) == [
            (0, 2, K.EXECUTE, "P1"),
            (2, 4, K.EXECUTE, "P2"),
            (4, 5, K.EXECUTE, "P3"),
            (5, 10, K.EXECUTE, "P1"),
        ]
        assert metrics_of(result, "P1") == {"CT": 10, "TAT": 10, "WT": 3, "RT": 0}
        assert metrics_of(result, "P2") == {"CT": 4, "TAT": 2, "WT": 0, "RT": 0}
        assert metrics_of(result, "P3") == {"CT": 5, "TAT": 1, "WT": 0, "RT": 0}
        assert result.metrics.average_waiting_time == pytest.approx(1.0)

    def test_idle_gap(self):
        processes = [Process("P1", 0, 2), Process("P2", 6, 1)]
        result = run_simulation("srtf", processes, SimulationConfig())
        assert as_tuples(result.timeline) == [
            (0, 2, K.EXECUTE, "P1"),
            (2, 6, K.IDLE, None),
            (6, 7, K.EXECUTE, "P2"),
        ]
        assert metrics_of(result, "P2") == {"CT": 7, "TAT": 1, "WT": 0, "RT": 0}
        assert result.metrics.cpu_utilization == pytest.approx(3 / 7)

    def test_is_preemptive_contrast_with_sjf(self):
        processes = [Process("P1", 0, 5), Process("P2", 1, 1)]
        result = run_simulation("srtf", processes, SimulationConfig())
        assert as_tuples(result.timeline) == [
            (0, 1, K.EXECUTE, "P1"),
            (1, 2, K.EXECUTE, "P2"),
            (2, 6, K.EXECUTE, "P1"),
        ]
        assert metrics_of(result, "P1") == {"CT": 6, "TAT": 6, "WT": 1, "RT": 0}
        assert metrics_of(result, "P2") == {"CT": 2, "TAT": 1, "WT": 0, "RT": 0}