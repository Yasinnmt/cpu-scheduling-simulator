"""Streamlit UI for the CPU scheduling simulator."""

import pandas as pd
import streamlit as st

from cpu_scheduler.core.scheduler import SimulationResult, run_simulation
from cpu_scheduler.metrics.calculator import MetricsReport
from cpu_scheduler.models.config import MLFQConfig, SimulationConfig
from cpu_scheduler.models.process import Process
from cpu_scheduler.validation.validators import ValidationError
from cpu_scheduler.visualization import draw_gantt, draw_metrics_comparison

ALGORITHMS = ["fcfs", "sjf", "srtf", "priority", "priority_np", "rr", "hrrn", "mlfq"]

_LABELS = {
    "fcfs": "FCFS (non-preemptive)",
    "sjf": "SJF (non-preemptive)",
    "srtf": "SRTF (preemptive)",
    "priority": "Priority (preemptive, aging)",
    "priority_np": "Priority (non-preemptive, aging)",
    "rr": "Round Robin",
    "hrrn": "HRRN (non-preemptive)",
    "mlfq": "MLFQ (multilevel feedback queue)",
}


def _as_int(value: object, label: str, row: int) -> int:
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValidationError(
            f"row {row}: {label} must be a number, got {value!r}"
        ) from None
    if not number.is_integer():
        raise ValidationError(
            f"row {row}: {label} must be a whole number, got {value!r}"
        )
    return int(number)


def parse_processes(table: pd.DataFrame) -> list[Process]:
    processes = []
    for index, row in table.iterrows():
        row_no = index + 1
        raw_pid = row["pid"]
        if pd.isna(raw_pid) or not str(raw_pid).strip():
            raise ValidationError(f"row {row_no}: pid is required")
        arrival = _as_int(row["arrival_time"], "arrival_time", row_no)
        burst = _as_int(row["burst_time"], "burst_time", row_no)
        priority = (
            0 if pd.isna(row["priority"])
            else _as_int(row["priority"], "priority", row_no)
        )
        processes.append(Process(str(raw_pid).strip(), arrival, burst, priority))
    return processes


def parse_quantums(text: str) -> tuple[int, ...]:
    parts = [part.strip() for part in text.split(",") if part.strip()]
    if not parts:
        raise ValidationError("MLFQ quantums: enter at least one level, e.g. 2, 4")
    quantums = []
    for part in parts:
        try:
            value = int(part)
        except ValueError:
            raise ValidationError(
                f"MLFQ quantums: {part!r} is not an integer"
            ) from None
        if value < 1:
            raise ValidationError(f"MLFQ quantums: {value} must be >= 1")
        quantums.append(value)
    return tuple(quantums)


def build_config(
    context_switch_cost: int,
    time_quantum: int,
    aging_interval: int,
    mlfq_quantums: tuple[int, ...],
    boost_interval: int,
) -> SimulationConfig:
    return SimulationConfig(
        context_switch_cost=int(context_switch_cost),
        time_quantum=int(time_quantum),
        aging_interval=int(aging_interval) or None,
        mlfq=MLFQConfig(quantums=mlfq_quantums, boost_interval=int(boost_interval)),
    )


def _show_result(result: SimulationResult) -> None:
    metrics = result.metrics
    st.subheader(f"Gantt chart — {_LABELS[result.algorithm]}")
    st.pyplot(draw_gantt(result.timeline, title=result.algorithm.upper()))
    st.subheader("Per-process metrics")
    st.dataframe(metrics.per_process, use_container_width=True, hide_index=True)
    cols = st.columns(7)
    cols[0].metric("Avg WT", f"{metrics.average_waiting_time:.2f}")
    cols[1].metric("Avg TAT", f"{metrics.average_turnaround_time:.2f}")
    cols[2].metric("Avg RT", f"{metrics.average_response_time:.2f}")
    cols[3].metric("CPU utilization", f"{metrics.cpu_utilization:.1%}")
    cols[4].metric("Throughput", f"{metrics.throughput:.3f}")
    cols[5].metric("Context switches", str(metrics.context_switch_count))
    cols[6].metric("Makespan", str(metrics.makespan))


def _comparison_table(reports: dict[str, MetricsReport]) -> pd.DataFrame:
    rows = {
        name: {
            "Avg WT": round(report.average_waiting_time, 3),
            "Avg TAT": round(report.average_turnaround_time, 3),
            "Avg RT": round(report.average_response_time, 3),
            "Utilization": round(report.cpu_utilization, 3),
            "CS count": report.context_switch_count,
        }
        for name, report in reports.items()
    }
    return pd.DataFrame.from_dict(rows, orient="index")


def main() -> None:
    st.set_page_config(page_title="CPU Scheduling Simulator", layout="wide")
    st.title("CPU Scheduling Simulator")
    st.caption("Tick-based simulation of FCFS, SJF, SRTF, Priority, RR, HRRN and MLFQ.")

    with st.sidebar:
        st.header("Parameters")
        algorithm = st.selectbox("Algorithm", ALGORITHMS, format_func=_LABELS.get)
        cs_cost = st.number_input("Context switch cost", min_value=0, value=1, step=1)
        quantum = st.number_input("Time quantum (Round Robin)", min_value=1, value=2, step=1)
        aging = st.number_input("Aging interval (0 = disabled)", min_value=0, value=0, step=1)
        st.subheader("MLFQ")
        quantums_text = st.text_input("Quantum per level (comma-separated)", value="2, 4")
        boost = st.number_input("Boost interval", min_value=1, value=20, step=1)

    st.subheader("Processes")
    default_table = pd.DataFrame(
        {
            "pid": ["P1", "P2", "P3"],
            "arrival_time": [0, 2, 9],
            "burst_time": [6, 2, 1],
            "priority": [2, 1, 3],
        }
    )
    table = st.data_editor(
        default_table,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "pid": st.column_config.TextColumn("PID", required=True),
            "arrival_time": st.column_config.NumberColumn(
                "Arrival", step=1, format="%d", min_value=0
            ),
            "burst_time": st.column_config.NumberColumn(
                "Burst", step=1, format="%d", min_value=1
            ),
            "priority": st.column_config.NumberColumn("Priority", step=1, format="%d"),
        },
    )

    if st.button("Run simulation", type="primary"):
        try:
            processes = parse_processes(table)
            config = build_config(
                cs_cost, quantum, aging, parse_quantums(quantums_text), boost
            )
            st.session_state["result"] = run_simulation(algorithm, processes, config)
        except ValidationError as exc:
            st.session_state.pop("result", None)
            st.error(str(exc))

    result: SimulationResult | None = st.session_state.get("result")
    if result is not None:
        _show_result(result)

    with st.expander("Compare algorithms"):
        chosen = st.multiselect(
            "Algorithms", ALGORITHMS, default=["fcfs", "sjf", "srtf"],
            format_func=_LABELS.get,
        )
        if st.button("Compare"):
            try:
                if not chosen:
                    raise ValidationError("select at least one algorithm to compare")
                processes = parse_processes(table)
                config = build_config(
                    cs_cost, quantum, aging, parse_quantums(quantums_text), boost
                )
                st.session_state["comparison"] = {
                    name: run_simulation(name, processes, config).metrics
                    for name in chosen
                }
            except ValidationError as exc:
                st.session_state.pop("comparison", None)
                st.error(str(exc))
        comparison: dict[str, MetricsReport] | None = st.session_state.get("comparison")
        if comparison:
            st.pyplot(draw_metrics_comparison(comparison))
            st.dataframe(_comparison_table(comparison), use_container_width=True)


if __name__ == "__main__":
    main()