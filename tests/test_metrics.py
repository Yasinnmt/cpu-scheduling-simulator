import pytest

from cpu_scheduler.metrics import MetricsCalculator
from cpu_scheduler.models import IntervalKind as K
from cpu_scheduler.models import Process, Timeline, TimelineEntry as E


def test_formulas_on_synthetic_timeline():
    # P1 runs 0-5, CS 5-6, P2 runs 6-9 (P2 arrived at 2).
    processes = [Process("P1", 0, 5), Process("P2", 2, 3)]
    timeline = Timeline([
        E(0, 5, K.EXECUTE, "P1"),
        E(5, 6, K.CONTEXT_SWITCH),
        E(6, 9, K.EXECUTE, "P2"),
    ])
    report = MetricsCalculator.compute(processes, timeline)
    rows = report.per_process.set_index("pid")
    assert rows.loc["P1", "completion_time"] == 5
    assert rows.loc["P1", "turnaround_time"] == 5
    assert rows.loc["P1", "waiting_time"] == 0
    assert rows.loc["P1", "response_time"] == 0
    assert rows.loc["P2", "completion_time"] == 9
    assert rows.loc["P2", "turnaround_time"] == 7
    assert rows.loc["P2", "waiting_time"] == 4
    assert rows.loc["P2", "response_time"] == 4
    assert report.average_waiting_time == pytest.approx(2.0)
    assert report.average_turnaround_time == pytest.approx(6.0)
    assert report.average_response_time == pytest.approx(2.0)
    assert report.cpu_utilization == pytest.approx(8 / 9)
    assert report.throughput == pytest.approx(2 / 9)
    assert report.context_switch_count == 1
    assert report.makespan == 9


def test_column_order():
    processes = [Process("P1", 0, 2)]
    timeline = Timeline([E(0, 2, K.EXECUTE, "P1")])
    report = MetricsCalculator.compute(processes, timeline)
    assert list(report.per_process.columns) == [
        "pid", "arrival_time", "burst_time", "completion_time",
        "turnaround_time", "waiting_time", "response_time",
    ]