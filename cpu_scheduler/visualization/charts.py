"""Statistical comparison charts built from MetricsReport summaries."""

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from cpu_scheduler.metrics.calculator import MetricsReport


def draw_bar_chart(names: list[str], values: list[float], title: str, ylabel: str) -> Figure:
    fig = Figure(figsize=(max(6.0, len(names) * 1.2), 4.0))
    FigureCanvasAgg(fig)
    ax = fig.add_subplot(111)
    bars = ax.bar(names, values, color="#1f77b4", edgecolor="black", linewidth=0.6)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{value:.3g}",
                ha="center", va="bottom", fontsize=9)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.margins(y=0.15)
    fig.tight_layout()
    return fig


def draw_metrics_comparison(reports: dict[str, MetricsReport]) -> Figure:
    names = list(reports)
    series = {
        "Avg WT": [reports[n].average_waiting_time for n in names],
        "Avg TAT": [reports[n].average_turnaround_time for n in names],
        "Avg RT": [reports[n].average_response_time for n in names],
    }
    fig = Figure(figsize=(max(7.0, len(names) * 1.5), 4.5))
    FigureCanvasAgg(fig)
    ax = fig.add_subplot(111)
    width = 0.25
    for i, (label, values) in enumerate(series.items()):
        positions = [x + (i - 1) * width for x in range(len(names))]
        ax.bar(positions, values, width, label=label, edgecolor="black", linewidth=0.5)
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names)
    ax.set_ylabel("Time units")
    ax.set_title("Average waiting / turnaround / response time")
    ax.legend()
    ax.margins(y=0.1)
    fig.tight_layout()
    return fig