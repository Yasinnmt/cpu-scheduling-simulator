"""Classic sequential Gantt chart: EXECUTE / IDLE / CONTEXT SWITCH blocks.

Uses the Agg backend directly so it works headless (tests) and inside
Streamlit alike. The engine is never imported here.
"""

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.patches import Patch

from cpu_scheduler.models.timeline import IntervalKind, Timeline

_IDLE_COLOR = "#d9d9d9"
_CS_COLOR = "#d62728"
_PROCESS_COLORS = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#9467bd", "#8c564b",
    "#e377c2", "#7f7f7f", "#bcbd22", "#17becf", "#aec7e8",
]


def draw_gantt(timeline: Timeline, title: str = "CPU Gantt Chart") -> Figure:
    width = max(8.0, min(20.0, timeline.makespan * 0.4))
    fig = Figure(figsize=(width, 3.2))
    FigureCanvasAgg(fig)
    ax = fig.add_subplot(111)
    entries = timeline.entries
    if not entries:
        ax.text(0.5, 0.5, "Empty timeline", ha="center", va="center",
                transform=ax.transAxes)
        ax.set_title(title)
        return fig

    pid_colors: dict[str, str] = {}
    for entry in entries:
        if entry.kind is IntervalKind.EXECUTE and entry.pid not in pid_colors:
            pid_colors[entry.pid] = _PROCESS_COLORS[len(pid_colors) % len(_PROCESS_COLORS)]

    for entry in entries:
        if entry.kind is IntervalKind.EXECUTE:
            color, label, hatch = pid_colors[entry.pid], entry.pid, None
        elif entry.kind is IntervalKind.IDLE:
            color, label, hatch = _IDLE_COLOR, "idle", ".."
        else:
            color, label, hatch = _CS_COLOR, "CS", "//"
        ax.barh(0, entry.duration, left=entry.start, height=0.6,
                color=color, edgecolor="black", linewidth=0.8, hatch=hatch)
        if entry.duration / timeline.makespan >= 0.03:
            ax.text((entry.start + entry.end) / 2, 0, label,
                    ha="center", va="center", fontsize=9,
                    color="white" if entry.kind is IntervalKind.CONTEXT_SWITCH else "black")

    boundaries = sorted({e.start for e in entries} | {e.end for e in entries})
    ax.set_yticks([])
    ax.set_xticks(boundaries)
    ax.set_xlim(entries[0].start, entries[-1].end)
    ax.set_ylim(-0.6, 0.6)
    ax.set_xlabel("Time")
    ax.set_title(title)

    handles = [
        Patch(facecolor=color, edgecolor="black", label=pid)
        for pid, color in pid_colors.items()
    ]
    handles.append(Patch(facecolor=_IDLE_COLOR, edgecolor="black", hatch="..", label="Idle"))
    handles.append(Patch(facecolor=_CS_COLOR, edgecolor="black", hatch="//",
                         label="Context switch"))
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.18),
              ncol=min(len(handles), 5), fontsize=8, frameon=False)
    fig.subplots_adjust(bottom=0.32)
    return fig