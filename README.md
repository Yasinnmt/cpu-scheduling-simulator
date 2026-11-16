# CPU Scheduling Simulator

A modular, tick-based CPU scheduling simulator built as an Operating Systems
course project. The simulation core is pure Python (OOP, type hints, no UI
dependencies); a Streamlit app provides the interactive interface and
Matplotlib renders the charts.

## Algorithms

| Key           | Algorithm                              | Preemptive |
|---------------|----------------------------------------|------------|
| `fcfs`        | First Come First Served                | no         |
| `sjf`         | Shortest Job First                     | no         |
| `srtf`        | Shortest Remaining Time First          | yes        |
| `priority`    | Priority scheduling with optional aging| yes        |
| `priority_np` | Priority scheduling with optional aging| no         |
| `rr`          | Round Robin (configurable quantum)     | yes        |
| `hrrn`        | Highest Response Ratio Next            | no         |
| `mlfq`        | Multilevel Feedback Queue              | yes        |

MLQ (plain multilevel queue, without feedback) is intentionally **not**
implemented, per the project specification.

## Quick start

```bash
pip install -r requirements.txt
streamlit run app.py        # interactive UI at http://localhost:8501
python -m pytest            # run the full test suite
```

Python 3.13 is used for development. On networks where PyPI is unreachable,
install from a mirror, e.g.
`pip install -i https://mirror-pypi.runflare.com/simple -r requirements.txt`.

## Project structure

```
app.py                        Streamlit UI (input parsing helpers + main())
cpu_scheduler/
  models/
    process.py                Process (immutable input), ProcessState (mutable runtime)
    config.py                 SimulationConfig, MLFQConfig (frozen dataclasses)
    timeline.py               TimelineEntry / Timeline: merged EXECUTE/IDLE/CONTEXT_SWITCH intervals
  validation/
    validators.py             input validation, ValidationError, workload size guard
  core/
    policy.py                 SchedulingPolicy: shared algorithm interface (strategy pattern)
    engine.py                 SimulationEngine: tick loop, dispatch, recording (algorithm-agnostic)
    context_switch.py         ContextSwitchManager: when a switch is charged
    aging.py                  AgingManager: effective priority from cumulative ready wait
    scheduler.py              run_simulation() facade + algorithm registry
  algorithms/                 one small decision class per algorithm (fcfs, sjf, srtf,
                              priority, round_robin, hrrn, mlfq)
  metrics/
    calculator.py             MetricsCalculator / MetricsReport (per-process + aggregates)
  visualization/
    gantt.py                  draw_gantt(timeline) -> Matplotlib Figure
    charts.py                 draw_bar_chart, draw_metrics_comparison
tests/                        235 pytest tests (golden examples, invariants, white-box, UI helpers)
```

## Architecture

- **Strategy pattern.** Every algorithm implements `SchedulingPolicy`
  (`on_arrival`, `pick_next`, `slice_length`, `on_slice_end`, optional
  `should_preempt`, `on_preempt`, `on_tick`). Algorithms only make decisions;
  the engine owns the clock, the CPU and all recording.
- **Fixed tick order.** At every integer tick `t`:
  1. admit arrivals at `t`;
  2. `on_tick` hook (aging needs no mutation; MLFQ boost happens here);
  3. slice-end handling (`on_slice_end` for the running process);
  4. preemption check (`should_preempt` / `on_preempt`);
  5. dispatch — insert a context switch first if one is charged;
  6. record the activity of `[t, t+1)` (execute / idle / context switch);
  7. accumulate ready-queue waiting time for arrived, unfinished, non-running
     processes (the CS target does not accrue wait during its switch).
- **Timeline as single source of truth.** Consecutive ticks of the same kind
  and pid are merged into intervals. Metrics and visualization only read the
  `Timeline`; the engine never imports visualization, and visualization never
  computes scheduling logic.

## Scheduling assumptions and policies

These conventions are fixed, documented, and covered by tests:

1. **Integer time.** All times are whole ticks; a tick is one time unit.
2. **No leading idle.** The timeline starts at the first arrival.
3. **Context switches.** Charged only between two *different* processes
   (never before the first process, never idle→process, never process→itself).
   A switch is atomic overhead: it is not busy time, and arrivals during a
   switch are considered at the next tick. `context_switch_cost = 0` disables
   switches entirely.
4. **Priority direction.** Lower number = higher priority.
5. **Tie-breaking.** Everywhere a choice exists: earlier arrival time first,
   then lexicographic pid. HRRN ratios are compared as exact `Fraction`s, so
   mathematically equal ratios really tie and fall through to this rule.
6. **Strict preemption.** A runner is preempted only by a *strictly* better
   candidate (SRTF: strictly smaller remaining time; priority: strictly better
   effective priority; MLFQ: strictly higher queue). Ties never cause churn.
7. **Round Robin boundary.** A process arriving exactly at a quantum-expiry
   tick enters the queue *before* the expired process is requeued. If the same
   process is reselected, no context switch is charged.
8. **Aging.** `effective_priority = base − (cumulative_ready_wait // interval)`.
   The wait counter is cumulative across preemptions. There is **no clamp**:
   the result may go below zero (even higher priority), which also makes
   negative base priorities work. `aging_interval = 0`/`None` disables aging.
9. **HRRN.** `ratio = (waiting + burst) / burst` with `waiting = now − arrival`,
   evaluated at dispatch time; non-preemptive.
10. **MLFQ.** Level 0 is the highest queue; new arrivals enter level 0. Each
    level is FIFO with its own quantum. Using a full quantum demotes one level
    (the bottom level stays). Preemption does **not** demote — the process
    returns to the tail of its own queue. Finishing exactly at quantum end is
    completion, not demotion. Every `boost_interval` ticks (absolute time,
    `t > 0`) all *waiting* processes move to level 0, preserving FIFO order
    level by level; the running process keeps its level for the current slice,
    so a boost can immediately preempt a runner below level 0.
11. **Utilization window.** From first arrival to last completion; only real
    execution counts as busy (idle and context switches are overhead).
12. **Validation.** `burst ≥ 1`, `arrival ≥ 0`, integers only (booleans
    rejected), non-empty unique pids; RR requires a quantum; MLFQ requires a
    config; a worst-case horizon guard rejects workloads above 1,000,000 ticks.

## Metrics

| Metric | Formula |
|--------|---------|
| Completion time (CT) | end of the process's last EXECUTE interval |
| Turnaround (TAT) | `CT − AT` |
| Waiting (WT) | `TAT − BT` (includes time lost to context-switch overhead) |
| Response (RT) | start of first EXECUTE interval `− AT` |
| CPU utilization | `Σ BT / makespan` |
| Throughput | `process count / makespan` |
| Context switches | number of CONTEXT_SWITCH intervals |
| Makespan | `last end − first start` of the timeline |

## Worked example (hand-verified)

Workload: `P1(AT=0, BT=6)`, `P2(AT=2, BT=2)`, `P3(AT=9, BT=1)`,
`context_switch_cost=1`, RR quantum 2, MLFQ quantums `(2, 4)` with boost 20.

Gantt traces:

- **FCFS:** P1 0–6, CS 6–7, P2 7–9, CS 9–10, P3 10–11
- **SRTF:** P1 0–2, CS 2–3, P2 3–5, CS 5–6, P1 6–10, CS 10–11, P3 11–12
- **MLFQ:** P1 0–2, CS 2–3, P2 3–5, CS 5–6, P1 6–9, CS 9–10, P3 10–11,
  CS 11–12, P1 12–13 (P3's arrival at t=9 preempts the level-1 runner)

| Algorithm | Avg WT | Avg TAT | Avg RT | Utilization | CS | Makespan |
|-----------|--------|---------|--------|-------------|----|----------|
| fcfs      | 2.00   | 5.00    | 2.00   | 81.8%       | 2  | 11       |
| sjf       | 2.00   | 5.00    | 2.00   | 81.8%       | 2  | 11       |
| srtf      | 2.33   | 5.33    | 1.00   | 75.0%       | 3  | 12       |
| rr        | 2.33   | 5.33    | 1.00   | 75.0%       | 3  | 12       |
| hrrn      | 2.00   | 5.00    | 2.00   | 81.8%       | 2  | 11       |
| mlfq      | 3.00   | 6.00    | 0.67   | 69.2%       | 4  | 13       |

Every number above was calculated by hand and is asserted as a literal in the
test suite (the code under test never computes its own expectations).

## Testing

```bash
python -m pytest
```

235 tests across 15 files:

- **Golden tests** per algorithm: hand-calculated CT/TAT/WT/RT and full Gantt
  interval lists, with and without context-switch cost.
- **Invariant suite**: 8 algorithm variants × 4 workloads × CS costs {0, 1, 3}
  checking timeline contiguity, conservation of burst time, metric identities
  (`TAT = WT + BT`, `WT ≥ RT ≥ 0`), and completion of every process.
- **White-box tests** for aging counters and MLFQ level transitions (demotion,
  no-demotion on preemption, boost ordering).
- **Validation tests** for every rejection rule.
- **Visualization tests** including real PNG rendering (magic-byte check).
- **UI helper tests** for the Streamlit input parsing (no browser needed).

## User interface

`streamlit run app.py` opens a page with an editable process table (add/remove
rows), an algorithm selector, and parameters for context-switch cost, RR
quantum, aging interval, and MLFQ quantums/boost. *Run simulation* shows the
Gantt chart (idle and context-switch intervals included), the per-process
metrics table, and summary cards; the *Compare algorithms* expander runs
several algorithms on the same workload and renders a comparison chart plus
table. Invalid input produces a clear error message instead of a result.