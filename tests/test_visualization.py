import io

import matplotlib

matplotlib.use("Agg")

import pytest
from matplotlib.figure import Figure

from cpu_scheduler.core.scheduler import run_simulation
from cpu_scheduler.models import IntervalKind as K
from cpu_scheduler.models import Process, SimulationConfig, Timeline, TimelineEntry as E
from cpu_scheduler.visualization import draw_bar_chart, draw_gantt, draw_metrics_comparison


@pytest.fixture
def timeline():
    return Timeline([
        E(0, 5, K.EXECUTE, "P1"),
        E(5, 6, K.CONTEXT_SWITCH),
        E(6, 9, K.EXECUTE, "P2"),
        E(9, 11, K.IDLE),
        E(11, 13, K.EXECUTE, "P1"),
    ])


class TestGantt:
    def test_one_bar_per_entry(self, timeline):
        fig = draw_gantt(timeline)
        assert isinstance(fig, Figure)
        assert len(fig.axes[0].patches) == len(timeline)

    def test_ticks_at_interval_boundaries(self, timeline):
        fig = draw_gantt(timeline)
        assert list(fig.axes[0].get_xticks()) == [0, 5, 6, 9, 11, 13]

    def test_labels_and_legend(self, timeline):
        ax = draw_gantt(timeline).axes[0]
        texts = [t.get_text() for t in ax.texts]
        for label in ("P1", "P2", "idle", "CS"):
            assert label in texts
        legend_labels = [t.get_text() for t in ax.get_legend().get_texts()]
        assert "Idle" in legend_labels
        assert "Context switch" in legend_labels

    def test_renders_to_png(self, timeline):
        buf = io.BytesIO()
        draw_gantt(timeline).savefig(buf, format="png")
        assert buf.getvalue().startswith(b"\x89PNG")

    def test_empty_timeline_does_not_crash(self):
        assert isinstance(draw_gantt(Timeline()), Figure)


class TestCharts:
    def test_bar_chart(self):
        fig = draw_bar_chart(["fcfs", "sjf"], [5.75, 4.0], "Avg WT", "time")
        ax = fig.axes[0]
        assert len(ax.patches) == 2
        assert ax.get_title() == "Avg WT"

    def test_metrics_comparison(self):
        processes = [Process("P1", 0, 5), Process("P2", 1, 3), Process("P3", 2, 8)]
        reports = {
            algo: run_simulation(algo, processes, SimulationConfig(time_quantum=2)).metrics
            for algo in ("fcfs", "sjf", "rr")
        }
        fig = draw_metrics_comparison(reports)
        ax = fig.axes[0]
        assert len(ax.patches) == 9  # 3 algorithms x 3 metrics
        assert [t.get_text() for t in ax.get_xticklabels()] == ["fcfs", "sjf", "rr"]

    def test_charts_render_to_png(self):
        fig = draw_bar_chart(["a", "b"], [1.0, 2.0], "t", "y")
        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        assert buf.getvalue().startswith(b"\x89PNG")