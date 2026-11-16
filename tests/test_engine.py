import pytest

from cpu_scheduler.algorithms.fcfs import FCFSPolicy
from cpu_scheduler.core.engine import SimulationEngine
from cpu_scheduler.models import IntervalKind as K
from cpu_scheduler.models import Process, SimulationConfig


def run_fcfs(processes, cs=0):
    engine = SimulationEngine(FCFSPolicy(), SimulationConfig(context_switch_cost=cs))
    timeline = engine.run(processes)
    return engine, timeline


def as_tuples(timeline):
    return [(e.start, e.end, e.kind, e.pid) for e in timeline]


class TestEngine:
    def test_idle_and_cs_intervals(self):
        processes = [Process("P1", 0, 3), Process("P2", 5, 2), Process("P3", 6, 1)]
        _, timeline = run_fcfs(processes, cs=1)
        assert as_tuples(timeline) == [
            (0, 3, K.EXECUTE, "P1"),
            (3, 5, K.IDLE, None),
            (5, 6, K.CONTEXT_SWITCH, None),
            (6, 8, K.EXECUTE, "P2"),
            (8, 9, K.CONTEXT_SWITCH, None),
            (9, 10, K.EXECUTE, "P3"),
        ]

    def test_timeline_starts_at_first_arrival(self):
        _, timeline = run_fcfs([Process("P1", 4, 2)], cs=3)
        assert as_tuples(timeline) == [(4, 6, K.EXECUTE, "P1")]
        assert timeline.makespan == 2

    def test_ready_wait_accumulation(self):
        processes = [Process("P1", 0, 3), Process("P2", 5, 2), Process("P3", 6, 1)]
        engine, _ = run_fcfs(processes, cs=1)
        assert engine.states["P1"].accumulated_ready_wait == 0
        # P2 was committed during the switch tick, so it never sat in the queue.
        assert engine.states["P2"].accumulated_ready_wait == 0
        # P3 waited in the ready queue during ticks 6 and 7.
        assert engine.states["P3"].accumulated_ready_wait == 2

    def test_first_start_and_completion_recorded(self):
        engine, _ = run_fcfs([Process("P1", 0, 3), Process("P2", 5, 2)], cs=1)
        assert engine.states["P2"].first_start == 6
        assert engine.states["P2"].completion_time == 8

    def test_deterministic(self):
        processes = [Process("P1", 0, 5), Process("P2", 1, 3), Process("P3", 2, 8)]
        _, t1 = run_fcfs(processes, cs=2)
        _, t2 = run_fcfs(processes, cs=2)
        assert as_tuples(t1) == as_tuples(t2)


WORKLOADS = [
    [Process("P1", 0, 5), Process("P2", 1, 3), Process("P3", 2, 8), Process("P4", 3, 6)],
    [Process("P1", 0, 3), Process("P2", 5, 2), Process("P3", 6, 1)],
    [Process("P1", 4, 2)],
    [Process("P1", 0, 2), Process("P2", 0, 2), Process("P3", 0, 3)],
]


@pytest.mark.parametrize(
    "algorithm", ["fcfs", "sjf", "srtf", "priority", "priority_np", "rr", "hrrn", "mlfq"]
)
@pytest.mark.parametrize("processes", WORKLOADS)
@pytest.mark.parametrize("cs", [0, 1, 3])
class TestInvariants:
    def test_contiguous_and_complete(self, algorithm, processes, cs):
        from cpu_scheduler.core.scheduler import run_simulation
        from cpu_scheduler.models import MLFQConfig

        config = SimulationConfig(
            context_switch_cost=cs,
            time_quantum=2 if algorithm == "rr" else None,
            mlfq=MLFQConfig(quantums=(2, 4), boost_interval=20)
            if algorithm == "mlfq"
            else None,
        )
        result = run_simulation(algorithm, processes, config)
        timeline = result.timeline
        entries = timeline.entries
        assert entries[0].start == min(p.arrival_time for p in processes)
        for a, b in zip(entries, entries[1:]):
            assert a.end == b.start
        assert timeline.busy_time == sum(p.burst_time for p in processes)
        for p in processes:
            assert sum(e.duration for e in timeline.segments_of(p.pid)) == p.burst_time
            assert timeline.completion_time(p.pid) >= p.arrival_time + p.burst_time
        frame = result.metrics.per_process
        assert (frame["waiting_time"] >= 0).all()
        assert (frame["response_time"] >= 0).all()