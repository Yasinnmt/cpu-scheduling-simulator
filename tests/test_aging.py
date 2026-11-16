from cpu_scheduler.core.aging import AgingManager
from cpu_scheduler.models import Process, ProcessState


def make_state(priority, wait):
    state = ProcessState(Process("P1", 0, 5, priority=priority))
    state.accumulated_ready_wait = wait
    return state


class TestAgingManager:
    def test_disabled_returns_base_priority(self):
        manager = AgingManager(None)
        assert not manager.enabled
        assert manager.effective_priority(make_state(3, 100)) == 3

    def test_improves_once_per_full_interval(self):
        manager = AgingManager(2)
        assert manager.enabled
        assert manager.effective_priority(make_state(5, 0)) == 5
        assert manager.effective_priority(make_state(5, 1)) == 5
        assert manager.effective_priority(make_state(5, 2)) == 4
        assert manager.effective_priority(make_state(5, 3)) == 4
        assert manager.effective_priority(make_state(5, 4)) == 3
        assert manager.effective_priority(make_state(5, 9)) == 1

    def test_can_go_below_zero(self):
        assert AgingManager(1).effective_priority(make_state(1, 5)) == -4

    def test_negative_base_priority_keeps_improving(self):
        assert AgingManager(2).effective_priority(make_state(-2, 4)) == -4