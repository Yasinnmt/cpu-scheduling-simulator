"""Per-process and aggregate metrics.

Formulas (documented assumptions):
CT = end of last EXECUTE interval; TAT = CT - AT; WT = TAT - BT;
RT = start of first EXECUTE interval - AT. WT therefore includes any time
spent waiting during context-switch overhead. Utilization counts only real
execution as busy (CS and idle are overhead), over the window from the first
arrival to the last completion.
"""

from dataclasses import dataclass

import pandas as pd

from cpu_scheduler.models.process import Process
from cpu_scheduler.models.timeline import Timeline

_COLUMNS = [
    "pid", "arrival_time", "burst_time", "completion_time",
    "turnaround_time", "waiting_time", "response_time",
]


@dataclass(frozen=True)
class MetricsReport:
    per_process: pd.DataFrame
    average_waiting_time: float
    average_turnaround_time: float
    average_response_time: float
    cpu_utilization: float
    throughput: float
    context_switch_count: int
    makespan: int


class MetricsCalculator:
    @staticmethod
    def compute(processes: list[Process], timeline: Timeline) -> MetricsReport:
        rows = []
        for p in processes:
            completion = timeline.completion_time(p.pid)
            first_start = timeline.first_execution_start(p.pid)
            turnaround = completion - p.arrival_time
            rows.append({
                "pid": p.pid,
                "arrival_time": p.arrival_time,
                "burst_time": p.burst_time,
                "completion_time": completion,
                "turnaround_time": turnaround,
                "waiting_time": turnaround - p.burst_time,
                "response_time": first_start - p.arrival_time,
            })
        frame = pd.DataFrame(rows, columns=_COLUMNS)
        makespan = timeline.makespan
        return MetricsReport(
            per_process=frame,
            average_waiting_time=float(frame["waiting_time"].mean()),
            average_turnaround_time=float(frame["turnaround_time"].mean()),
            average_response_time=float(frame["response_time"].mean()),
            cpu_utilization=timeline.busy_time / makespan,
            throughput=len(processes) / makespan,
            context_switch_count=timeline.context_switch_count,
            makespan=makespan,
        )