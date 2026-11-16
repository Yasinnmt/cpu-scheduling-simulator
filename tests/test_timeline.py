import pytest

from cpu_scheduler.models import IntervalKind as K
from cpu_scheduler.models import Timeline, TimelineEntry as E


@pytest.fixture
def timeline():
    # P1 runs 0-5, CS 5-6, P2 runs 6-9, idle 9-11, P1 runs 11-13.
    return Timeline([
        E(0, 5, K.EXECUTE, "P1"),
        E(5, 6, K.CONTEXT_SWITCH),
        E(6, 9, K.EXECUTE, "P2"),
        E(9, 11, K.IDLE),
        E(11, 13, K.EXECUTE, "P1"),
    ])


class TestTimelineEntry:
    def test_duration(self):
        assert E(3, 10, K.EXECUTE, "P1").duration == 7

    def test_invalid_durations_raise(self):
        with pytest.raises(ValueError):
            E(5, 5, K.IDLE)
        with pytest.raises(ValueError):
            E(7, 3, K.IDLE)
        with pytest.raises(ValueError):
            E(-1, 2, K.IDLE)

    def test_pid_rules_raise(self):
        with pytest.raises(ValueError):
            E(0, 2, K.EXECUTE)
        with pytest.raises(ValueError):
            E(0, 2, K.EXECUTE, "")
        with pytest.raises(ValueError):
            E(0, 2, K.IDLE, "P1")
        with pytest.raises(ValueError):
            E(0, 2, K.CONTEXT_SWITCH, "P1")


class TestTimeline:
    def test_busy_idle_cs_times(self, timeline):
        assert timeline.busy_time == 10
        assert timeline.idle_time == 2
        assert timeline.context_switch_time == 1
        assert timeline.context_switch_count == 1

    def test_makespan_and_bounds(self, timeline):
        assert timeline.makespan == 13
        assert timeline.first_start == 0
        assert timeline.last_end == 13

    def test_makespan_excludes_time_before_first_arrival(self):
        t = Timeline([E(5, 8, K.EXECUTE, "P1")])
        assert t.makespan == 3

    def test_segments_and_times_per_process(self, timeline):
        assert len(timeline.segments_of("P1")) == 2
        assert timeline.first_execution_start("P1") == 0
        assert timeline.completion_time("P1") == 13
        assert timeline.first_execution_start("P2") == 6
        assert timeline.completion_time("P2") == 9

    def test_unknown_pid(self, timeline):
        assert timeline.segments_of("PX") == ()
        assert timeline.first_execution_start("PX") is None
        assert timeline.completion_time("PX") is None

    def test_empty_timeline(self):
        t = Timeline()
        assert len(t) == 0
        assert t.makespan == 0
        assert t.busy_time == 0
        assert t.idle_time == 0
        assert t.context_switch_time == 0
        assert t.context_switch_count == 0
        assert t.first_start is None
        assert t.last_end is None

    def test_append_len_iter(self):
        t = Timeline()
        t.append(E(0, 2, K.EXECUTE, "P1"))
        t.append(E(2, 4, K.IDLE))
        assert len(t) == 2
        assert [e.start for e in t] == [0, 2]
        assert t.entries[-1].kind is K.IDLE