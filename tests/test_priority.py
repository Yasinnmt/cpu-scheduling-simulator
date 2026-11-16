"""Golden priority examples: every expected number below is calculated by hand."""

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


class TestNonPreemptive:
    def test_textbook_example(self):
        # P1 0-4 (runs to completion), P2 4-7 (pr 1), P3 7-9 (pr 2).
        processes = [
            Process("P1", 0, 4, priority=3),
            Process("P2", 1, 3, priority=1),
            Process("P3", 2, 2, priority=2),
        ]
        result = run_simulation("priority_np", processes, SimulationConfig())
        assert as_tuples(result.timeline) == [
            (0, 4, K.EXECUTE, "P1"),
            (4, 7, K.EXECUTE, "P2"),
            (7, 9, K.EXECUTE, "P3"),
        ]
        assert metrics_of(result, "P1") == {"CT": 4, "TAT": 4, "WT": 0, "RT": 0}
        assert metrics_of(result, "P2") == {"CT": 7, "TAT": 6, "WT": 3, "RT": 3}
        assert metrics_of(result, "P3") == {"CT": 9, "TAT": 7, "WT": 5, "RT": 5}
        m = result.metrics
        assert m.average_waiting_time == pytest.approx(8 / 3)
        assert m.average_turnaround_time == pytest.approx(17 / 3)
        assert m.cpu_utilization == pytest.approx(1.0)
        assert m.context_switch_count == 0

    def test_equal_priority_tie_break_by_pid(self):
        processes = [Process("P2", 0, 2, priority=1), Process("P1", 0, 2, priority=1)]
        result = run_simulation("priority_np", processes, SimulationConfig())
        assert as_tuples(result.timeline) == [
            (0, 2, K.EXECUTE, "P1"),
            (2, 4, K.EXECUTE, "P2"),
        ]

    def test_default_priorities_behave_like_fcfs(self):
        processes = [Process("P2", 0, 2), Process("P1", 1, 2)]
        result = run_simulation("priority_np", processes, SimulationConfig())
        assert as_tuples(result.timeline) == [
            (0, 2, K.EXECUTE, "P2"),
            (2, 4, K.EXECUTE, "P1"),
        ]

    def test_aging_changes_selection_order(self):
        # Without aging P3 (pr 1) would run before P2 (pr 2). With interval=1,
        # at t=2 both have effective priority 0 and P2 wins by arrival time.
        processes = [
            Process("P1", 0, 2, priority=0),
            Process("P2", 0, 2, priority=2),
            Process("P3", 1, 2, priority=1),
        ]
        config = SimulationConfig(aging_interval=1)
        result = run_simulation("priority_np", processes, config)
        assert as_tuples(result.timeline) == [
            (0, 2, K.EXECUTE, "P1"),
            (2, 4, K.EXECUTE, "P2"),
            (4, 6, K.EXECUTE, "P3"),
        ]
        assert metrics_of(result, "P2") == {"CT": 4, "TAT": 4, "WT": 2, "RT": 2}
        assert metrics_of(result, "P3") == {"CT": 6, "TAT": 5, "WT": 3, "RT": 3}

        without_aging = run_simulation("priority_np", processes, SimulationConfig())
        assert as_tuples(without_aging.timeline) == [
            (0, 2, K.EXECUTE, "P1"),
            (2, 4, K.EXECUTE, "P3"),
            (4, 6, K.EXECUTE, "P2"),
        ]


class TestPreemptive:
    def test_textbook_example(self):
        # P1 0-1, P2 1-4 (pr 1 preempts pr 3), P3 4-6, P1 6-9.
        processes = [
            Process("P1", 0, 4, priority=3),
            Process("P2", 1, 3, priority=1),
            Process("P3", 2, 2, priority=2),
        ]
        result = run_simulation("priority", processes, SimulationConfig())
        assert as_tuples(result.timeline) == [
            (0, 1, K.EXECUTE, "P1"),
            (1, 4, K.EXECUTE, "P2"),
            (4, 6, K.EXECUTE, "P3"),
            (6, 9, K.EXECUTE, "P1"),
        ]
        assert metrics_of(result, "P1") == {"CT": 9, "TAT": 9, "WT": 5, "RT": 0}
        assert metrics_of(result, "P2") == {"CT": 4, "TAT": 3, "WT": 0, "RT": 0}
        assert metrics_of(result, "P3") == {"CT": 6, "TAT": 4, "WT": 2, "RT": 2}
        m = result.metrics
        assert m.average_waiting_time == pytest.approx(7 / 3)
        assert m.average_response_time == pytest.approx(2 / 3)
        assert m.cpu_utilization == pytest.approx(1.0)

    def test_preemption_with_cs_overhead(self):
        # P1 0-2, CS 2-3, P2 3-5, CS 5-6, P1 6-9.
        processes = [Process("P1", 0, 5, priority=2), Process("P2", 2, 2, priority=0)]
        result = run_simulation("priority", processes, SimulationConfig(context_switch_cost=1))
        assert as_tuples(result.timeline) == [
            (0, 2, K.EXECUTE, "P1"),
            (2, 3, K.CONTEXT_SWITCH, None),
            (3, 5, K.EXECUTE, "P2"),
            (5, 6, K.CONTEXT_SWITCH, None),
            (6, 9, K.EXECUTE, "P1"),
        ]
        assert metrics_of(result, "P1") == {"CT": 9, "TAT": 9, "WT": 4, "RT": 0}
        assert metrics_of(result, "P2") == {"CT": 5, "TAT": 3, "WT": 1, "RT": 1}
        assert result.metrics.context_switch_count == 2
        assert result.metrics.cpu_utilization == pytest.approx(7 / 9)

    def test_equal_priority_does_not_preempt(self):
        processes = [Process("P1", 0, 4, priority=1), Process("P2", 1, 2, priority=1)]
        result = run_simulation("priority", processes, SimulationConfig())
        assert as_tuples(result.timeline) == [
            (0, 4, K.EXECUTE, "P1"),
            (4, 6, K.EXECUTE, "P2"),
        ]

    def test_aging_prevents_starvation(self):
        # PL (pr 3) waits while PA and PB (pr 1) run. At t=4 its effective
        # priority is 3 - 4//2 = 1, tying PC (pr 1); PL wins by arrival time.
        processes = [
            Process("PL", 0, 2, priority=3),
            Process("PA", 0, 2, priority=1),
            Process("PB", 2, 2, priority=1),
            Process("PC", 4, 2, priority=1),
        ]
        config = SimulationConfig(aging_interval=2)
        result = run_simulation("priority", processes, config)
        assert as_tuples(result.timeline) == [
            (0, 2, K.EXECUTE, "PA"),
            (2, 4, K.EXECUTE, "PB"),
            (4, 6, K.EXECUTE, "PL"),
            (6, 8, K.EXECUTE, "PC"),
        ]
        assert metrics_of(result, "PL") == {"CT": 6, "TAT": 6, "WT": 4, "RT": 4}
        assert metrics_of(result, "PC") == {"CT": 8, "TAT": 4, "WT": 2, "RT": 2}
        assert result.metrics.average_waiting_time == pytest.approx(1.5)

        # Without aging, PL starves until every pr-1 job has finished.
        without_aging = run_simulation("priority", processes, SimulationConfig())
        assert as_tuples(without_aging.timeline) == [
            (0, 2, K.EXECUTE, "PA"),
            (2, 4, K.EXECUTE, "PB"),
            (4, 6, K.EXECUTE, "PC"),
            (6, 8, K.EXECUTE, "PL"),
        ]
        assert metrics_of(without_aging, "PL") == {"CT": 8, "TAT": 8, "WT": 6, "RT": 6}