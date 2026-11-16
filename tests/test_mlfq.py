"""Golden MLFQ examples: every expected number below is calculated by hand."""

import pytest

from cpu_scheduler.algorithms.mlfq import MLFQPolicy
from cpu_scheduler.core.scheduler import run_simulation
from cpu_scheduler.models import IntervalKind as K
from cpu_scheduler.models import MLFQConfig, Process, ProcessState, SimulationConfig


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


def config(quantums, boost=100, cs=0):
    return SimulationConfig(
        context_switch_cost=cs, mlfq=MLFQConfig(quantums=quantums, boost_interval=boost)
    )


class TestGoldenExamples:
    def test_demotion_and_finish_at_quantum_end(self):
        # P1 0-2 (q0=2, demoted), P2 2-4 (finishes exactly at quantum end),
        # P1 4-7 from level 1.
        processes = [Process("P1", 0, 5), Process("P2", 1, 2)]
        result = run_simulation("mlfq", processes, config((2, 4)))
        assert as_tuples(result.timeline) == [
            (0, 2, K.EXECUTE, "P1"),
            (2, 4, K.EXECUTE, "P2"),
            (4, 7, K.EXECUTE, "P1"),
        ]
        assert metrics_of(result, "P1") == {"CT": 7, "TAT": 7, "WT": 2, "RT": 0}
        assert metrics_of(result, "P2") == {"CT": 4, "TAT": 3, "WT": 1, "RT": 1}
        assert result.metrics.average_waiting_time == pytest.approx(1.5)

    def test_cross_level_preemption(self):
        # P1 demoted to level 1 at t=2; P2 arrives at t=3 in level 0 and
        # preempts it. P1 keeps level 1 (no demotion on preemption).
        processes = [Process("P1", 0, 8), Process("P2", 3, 2)]
        result = run_simulation("mlfq", processes, config((2, 4)))
        assert as_tuples(result.timeline) == [
            (0, 3, K.EXECUTE, "P1"),
            (3, 5, K.EXECUTE, "P2"),
            (5, 10, K.EXECUTE, "P1"),
        ]
        assert metrics_of(result, "P1") == {"CT": 10, "TAT": 10, "WT": 2, "RT": 0}
        assert metrics_of(result, "P2") == {"CT": 5, "TAT": 2, "WT": 0, "RT": 0}

    def test_boost_changes_order(self):
        # At t=6 (boost) waiting PB moves to level 0, which immediately
        # preempts the level-1 runner PA. PB then runs 6-8 before PC.
        # Without boost, PA keeps running until PC arrives at t=7.
        processes = [Process("PA", 0, 6), Process("PB", 0, 6), Process("PC", 7, 2)]
        result = run_simulation("mlfq", processes, config((2, 4), boost=6))
        assert as_tuples(result.timeline) == [
            (0, 2, K.EXECUTE, "PA"),
            (2, 4, K.EXECUTE, "PB"),
            (4, 6, K.EXECUTE, "PA"),
            (6, 8, K.EXECUTE, "PB"),
            (8, 10, K.EXECUTE, "PC"),
            (10, 12, K.EXECUTE, "PA"),
            (12, 14, K.EXECUTE, "PB"),
        ]
        assert metrics_of(result, "PA") == {"CT": 12, "TAT": 12, "WT": 6, "RT": 0}
        assert metrics_of(result, "PB") == {"CT": 14, "TAT": 14, "WT": 8, "RT": 2}
        assert metrics_of(result, "PC") == {"CT": 10, "TAT": 3, "WT": 1, "RT": 1}
        assert result.metrics.average_waiting_time == pytest.approx(5.0)

        without_boost = run_simulation("mlfq", processes, config((2, 4), boost=100))
        assert as_tuples(without_boost.timeline) == [
            (0, 2, K.EXECUTE, "PA"),
            (2, 4, K.EXECUTE, "PB"),
            (4, 7, K.EXECUTE, "PA"),
            (7, 9, K.EXECUTE, "PC"),
            (9, 13, K.EXECUTE, "PB"),
            (13, 14, K.EXECUTE, "PA"),
        ]

    def test_three_level_demotion_chain(self):
        # P1: level 0 (0-1), level 1 (2-4), level 2 (4-8).
        processes = [Process("P1", 0, 7), Process("P2", 1, 1)]
        result = run_simulation("mlfq", processes, config((1, 2, 4)))
        assert as_tuples(result.timeline) == [
            (0, 1, K.EXECUTE, "P1"),
            (1, 2, K.EXECUTE, "P2"),
            (2, 8, K.EXECUTE, "P1"),
        ]
        assert metrics_of(result, "P1") == {"CT": 8, "TAT": 8, "WT": 1, "RT": 0}
        assert metrics_of(result, "P2") == {"CT": 2, "TAT": 1, "WT": 0, "RT": 0}

    def test_single_level_degenerates_to_rr(self):
        processes = [Process("P1", 0, 4), Process("P2", 0, 2)]
        result = run_simulation("mlfq", processes, config((3,), boost=10))
        assert as_tuples(result.timeline) == [
            (0, 3, K.EXECUTE, "P1"),
            (3, 5, K.EXECUTE, "P2"),
            (5, 6, K.EXECUTE, "P1"),
        ]
        assert metrics_of(result, "P1") == {"CT": 6, "TAT": 6, "WT": 2, "RT": 0}
        assert metrics_of(result, "P2") == {"CT": 5, "TAT": 5, "WT": 3, "RT": 3}

    def test_cs_cost_and_idle_gap(self):
        processes = [Process("P1", 0, 2), Process("P2", 4, 2)]
        result = run_simulation("mlfq", processes, config((2, 4), cs=1))
        assert as_tuples(result.timeline) == [
            (0, 2, K.EXECUTE, "P1"),
            (2, 4, K.IDLE, None),
            (4, 5, K.CONTEXT_SWITCH, None),
            (5, 7, K.EXECUTE, "P2"),
        ]
        assert metrics_of(result, "P2") == {"CT": 7, "TAT": 3, "WT": 1, "RT": 1}
        assert result.metrics.cpu_utilization == pytest.approx(4 / 7)
        assert result.metrics.context_switch_count == 1


class TestPolicyInternals:
    def test_preemption_does_not_demote_but_slice_end_does(self):
        policy = MLFQPolicy(MLFQConfig(quantums=(2, 4, 8), boost_interval=100))
        state = ProcessState(Process("P1", 0, 10))
        policy.on_arrival(state, 0)
        assert policy._level["P1"] == 0
        policy.on_slice_end(state, 2)
        assert policy._level["P1"] == 1
        policy.on_preempt(state, 3)
        assert policy._level["P1"] == 1
        policy.on_slice_end(state, 7)
        assert policy._level["P1"] == 2
        policy.on_slice_end(state, 15)
        assert policy._level["P1"] == 2  # bottom level stays

    def test_boost_resets_all_levels(self):
        policy = MLFQPolicy(MLFQConfig(quantums=(2, 4), boost_interval=6))
        a = ProcessState(Process("PA", 0, 8))
        b = ProcessState(Process("PB", 0, 8))
        policy.on_arrival(a, 0)
        policy.on_arrival(b, 0)
        policy.on_slice_end(a, 2)
        policy.on_slice_end(b, 4)
        assert policy._level == {"PA": 1, "PB": 1}
        policy.on_tick(6)
        assert policy._level == {"PA": 0, "PB": 0}
        assert policy.pick_next(6) is a
        assert policy.pick_next(6) is b